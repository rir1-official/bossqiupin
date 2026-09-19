"""Deterministic cleaning and feature engineering for Himalayas job records."""

import argparse
import csv
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data/raw/himalayas_api/2026-09-08"
RAW_ROOTS = (PROJECT_ROOT / "data/raw", PROJECT_ROOT / "data/raw_responses")

TRACE_FIELDS = ("source_url", "crawl_time", "data_origin")
EXPECTED_SOURCE_FIELDS = (
    "job_id",
    "job_title",
    "company_name",
    "city",
    "district",
    "salary_raw",
    "experience_raw",
    "education",
    "publish_date",
    "job_description",
    "industry",
    "company_type",
    "company_size",
    "skills",
    "job_category",
    "longitude",
    "latitude",
    "source",
    "source_url",
    "crawl_time",
    "data_origin",
)

SALARY_PATTERN = re.compile(
    r"^(?P<currency>[A-Za-z]{3})\s+"
    r"(?:(?P<direction>up to|from)\s+)?"
    r"(?P<first>[\d,.]+)"
    r"(?:-(?P<second>[\d,.]+))?"
    r"(?:\s+(?P<period>[A-Za-z]+))?$",
    re.IGNORECASE,
)
PERIOD_FACTORS = {
    "annual": 1.0,
    "annually": 1.0,
    "yearly": 1.0,
    "monthly": 12.0,
    "weekly": 52.0,
    "daily": 260.0,
    "hourly": 2080.0,
}
EXPERIENCE_RANGES = {
    "entry-level": (0.0, 2.0),
    "mid-level": (2.0, 5.0),
    "senior": (5.0, 10.0),
    "manager": (5.0, 12.0),
    "director": (8.0, 15.0),
    "executive": (10.0, 20.0),
}
STRUCTURE_TERMS = (
    "responsibilities",
    "requirements",
    "qualifications",
    "what you will do",
    "what you'll do",
    "benefits",
    "about the role",
)
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "we",
    "will",
    "with",
    "you",
    "your",
}

BROAD_CATEGORY_RULES = (
    ("Data Science", ("data", "analytics", "machine learning", "ai ", "artificial intelligence", "bi ")),
    ("Engineering", ("developer", "engineer", "software", "devops", "backend", "frontend", "full stack", "security")),
    ("Sales", ("sales", "account executive", "business development")),
    ("Customer Service", ("customer service", "customer support", "customer success")),
    ("Marketing", ("marketing", "growth", "seo", "social media")),
    ("Operations", ("operations", "project management", "program management")),
    ("Product", ("product",)),
    ("Finance", ("finance", "accounting", "financial")),
    ("Human Resources", ("human resources", "recruit", "talent", "people operations")),
    ("Healthcare", ("healthcare", "health care", "medical", "clinical")),
    ("Design", ("design", "ux", "ui ")),
    ("Legal", ("legal", "attorney", "lawyer", "counsel")),
    ("Education", ("education", "teacher", "instructor")),
)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def ensure_derived_output(path: Path) -> None:
    """Refuse writes into either immutable raw-data tree."""
    if any(_is_within(path, root) for root in RAW_ROOTS):
        raise ValueError("Derived output cannot be written under data/raw or data/raw_responses")


def natural_page_number(path: Path) -> int:
    match = re.search(r"_(\d+)\.jsonl$", path.name)
    return int(match.group(1)) if match else 0


def source_files(input_dir: Path) -> List[Path]:
    """Return only the dated source-page files, never historical aggregates."""
    if input_dir.resolve() != DEFAULT_INPUT_DIR.resolve():
        raise ValueError(f"Input directory must be the authorized dated source: {DEFAULT_INPUT_DIR}")
    files = sorted(input_dir.glob("remote_all_*.jsonl"), key=natural_page_number)
    if any(path.name == "jobs_all.jsonl" for path in files):
        raise ValueError("Historical aggregate jobs_all.jsonl must not be merged")
    return files


def load_source_records(input_dir: Path = DEFAULT_INPUT_DIR) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for path in source_files(input_dir):
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                row["raw_page_file"] = path.name
                row["raw_line_number"] = line_number
                records.append(row)
    return records


def stable_dedupe_key(record: Dict[str, Any]) -> Tuple[str, ...]:
    source = normalize_whitespace(record.get("source", "")).lower()
    job_id = normalize_whitespace(record.get("job_id", "")).lower()
    if source and job_id:
        return ("source_job_id", source, job_id)
    source_url = normalize_whitespace(record.get("source_url", "")).lower()
    if source_url:
        return ("source_url", source_url)
    values = tuple(
        normalize_whitespace(record.get(field, "")).lower()
        for field in ("job_title", "company_name", "city", "salary_raw", "publish_date")
    )
    return ("business_fields",) + values


def deduplicate_records(records: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    unique: List[Dict[str, Any]] = []
    duplicates: List[Dict[str, Any]] = []
    seen: Dict[Tuple[str, ...], int] = {}
    for row in records:
        key = stable_dedupe_key(row)
        if key in seen:
            duplicate = dict(row)
            duplicate["duplicate_of_index"] = seen[key]
            duplicate["dedupe_key_type"] = key[0]
            duplicates.append(duplicate)
            continue
        seen[key] = len(unique)
        unique.append(row)
    return unique, duplicates


def normalize_whitespace(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_text(value: Any) -> str:
    text = normalize_whitespace(value).lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[^\w+#.\-/\s]", " ", text, flags=re.UNICODE)
    return normalize_whitespace(text)


def tokenize_text(value: Any) -> List[str]:
    """Use jieba for mixed-language segmentation, then normalize tokens."""
    cleaned = clean_text(value)
    try:
        import jieba

        chunks = jieba.lcut(cleaned, cut_all=False)
    except ImportError:
        chunks = [cleaned]
    tokens: List[str] = []
    for chunk in chunks:
        for token in re.findall(r"[a-z0-9][a-z0-9+#.\-/]*|[\u4e00-\u9fff]+", chunk.lower()):
            token = token.strip("-./")
            if len(token) > 1 and token not in STOP_WORDS:
                tokens.append(token)
    return tokens


def split_skills(value: Any) -> List[str]:
    seen = set()
    skills: List[str] = []
    raw_values = value if isinstance(value, list) else str(value or "").split(",")
    for raw in raw_values:
        skill = normalize_whitespace(raw).replace("-", " ").lower()
        skill = normalize_whitespace(skill)
        if skill and skill not in seen:
            seen.add(skill)
            skills.append(skill)
    return skills


def parse_salary(value: Any) -> Dict[str, Any]:
    raw = normalize_whitespace(value)
    result: Dict[str, Any] = {
        "salary_currency": "",
        "salary_period": "",
        "salary_min": None,
        "salary_max": None,
        "salary_avg": None,
        "salary_min_annual": None,
        "salary_max_annual": None,
        "salary_avg_annual": None,
        "salary_parse_status": "missing" if not raw else "unparsed",
        "salary_outlier": False,
    }
    if not raw:
        return result
    match = SALARY_PATTERN.match(raw)
    if not match:
        return result
    currency = match.group("currency").upper()
    period = (match.group("period") or "").lower()
    first = float(match.group("first").replace(",", ""))
    second_raw = match.group("second")
    direction = (match.group("direction") or "").lower()
    if direction == "up to":
        minimum, maximum = None, first
    elif direction == "from":
        minimum, maximum = first, None
    elif second_raw:
        minimum, maximum = first, float(second_raw.replace(",", ""))
    else:
        minimum = maximum = first
    numeric = [amount for amount in (minimum, maximum) if amount is not None]
    average = sum(numeric) / len(numeric) if numeric else None
    factor = PERIOD_FACTORS.get(period)
    annual_min = minimum * factor if minimum is not None and factor else None
    annual_max = maximum * factor if maximum is not None and factor else None
    annual_avg = average * factor if average is not None and factor else None
    invalid_range = minimum is not None and maximum is not None and minimum > maximum
    outlier = invalid_range or bool(annual_avg is not None and (annual_avg < 5_000 or annual_avg > 1_000_000))
    result.update(
        {
            "salary_currency": currency,
            "salary_period": period,
            "salary_min": minimum,
            "salary_max": maximum,
            "salary_avg": average,
            "salary_min_annual": annual_min,
            "salary_max_annual": annual_max,
            "salary_avg_annual": annual_avg,
            "salary_parse_status": "parsed",
            "salary_outlier": outlier,
        }
    )
    return result


def parse_experience(value: Any) -> Dict[str, Any]:
    levels = [normalize_whitespace(part).lower() for part in str(value or "").split(",") if normalize_whitespace(part)]
    ranges = [EXPERIENCE_RANGES[level] for level in levels if level in EXPERIENCE_RANGES]
    return {
        "experience_level_primary": levels[0].title() if levels else "Unknown",
        "experience_year_min": min((pair[0] for pair in ranges), default=None),
        "experience_year_max": max((pair[1] for pair in ranges), default=None),
        "is_fresh_graduate": "entry-level" in levels,
        "experience_parse_status": "mapped" if ranges else ("missing" if not levels else "unmapped"),
    }


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    text = normalize_whitespace(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def classify_broad_category(record: Dict[str, Any]) -> str:
    haystack = " ".join(
        clean_text(record.get(field, "")).replace("-", " ")
        for field in ("job_category", "job_title", "skills")
    )
    for label, keywords in BROAD_CATEGORY_RULES:
        if any(keyword in haystack for keyword in keywords):
            return label
    return "Other"


def quality_components(row: Dict[str, Any]) -> Dict[str, int]:
    description_length = int(row.get("description_length") or 0)
    structure_count = int(row.get("description_structure_count") or 0)
    skill_count = int(row.get("skill_count") or 0)
    publish_age_days = row.get("publish_age_days")
    core_present = all(normalize_whitespace(row.get(field, "")) for field in ("job_title", "company_name", "city", "source"))
    provenance_present = all(normalize_whitespace(row.get(field, "")) for field in TRACE_FIELDS)
    description_length_points = min(15, math.ceil(description_length / 500)) if description_length else 0
    skill_points = min(20, skill_count * 2)
    salary_present = row.get("salary_parse_status") == "parsed"
    salary_has_bounds = row.get("salary_min") is not None and row.get("salary_max") is not None
    salary_annual_valid = row.get("salary_avg_annual") is not None and not row.get("salary_outlier")
    return {
        "quality_provenance_points": 5 if provenance_present else 0,
        "quality_core_points": 10 if core_present else 0,
        "quality_location_points": 5 if normalize_whitespace(row.get("district", "")) else 0,
        "quality_description_points": (5 if description_length else 0)
        + description_length_points
        + min(5, structure_count),
        "quality_salary_points": (5 if salary_present else 0)
        + (5 if salary_has_bounds else 0)
        + (5 if salary_annual_valid else 0),
        "quality_skill_points": skill_points,
        "quality_experience_points": 10 if row.get("experience_parse_status") == "mapped" else 0,
        "quality_recency_points": 5 if publish_age_days is not None and publish_age_days <= 30 else 0,
        "quality_category_points": 5 if normalize_whitespace(row.get("job_category", "")) else 0,
    }


def clean_record(record: Dict[str, Any], reference_time: Optional[datetime] = None) -> Dict[str, Any]:
    row = {field: record.get(field, "") for field in EXPECTED_SOURCE_FIELDS}
    row["raw_page_file"] = record.get("raw_page_file", "")
    row["raw_line_number"] = record.get("raw_line_number", "")
    for field in EXPECTED_SOURCE_FIELDS:
        if field != "skills":
            row[field] = normalize_whitespace(row[field])
    if row["city"] != "Remote":
        raise ValueError("Himalayas records must retain city=Remote")
    missing_trace = [field for field in TRACE_FIELDS if not row[field]]
    if missing_trace:
        raise ValueError(f"Traceability fields are missing: {', '.join(missing_trace)}")

    description_clean = clean_text(row["job_description"])
    skills = split_skills(row["skills"])
    salary = parse_salary(row["salary_raw"])
    experience = parse_experience(row["experience_raw"])
    published = parse_iso_datetime(row["publish_date"])
    reference = reference_time or datetime(2026, 9, 8, tzinfo=timezone.utc)
    publish_age_days = max(0, (reference - published).days) if published else None

    row.update(salary)
    row.update(experience)
    row.update(
        {
            "description_clean": description_clean,
            "description_tokens": " ".join(tokenize_text(description_clean)),
            "description_length": len(description_clean),
            "description_word_count": len(description_clean.split()),
            "description_structure_count": sum(term in description_clean for term in STRUCTURE_TERMS),
            "skills_normalized": " | ".join(skills),
            "skill_count": len(skills),
            "location_restriction_count": len([part for part in row["district"].split(",") if part.strip()]),
            "publish_age_days": publish_age_days,
            "broad_category": classify_broad_category(row),
            "is_it_data_role": classify_broad_category(row) in {"Data Science", "Engineering"},
        }
    )
    components = quality_components(row)
    row.update(components)
    row["quality_score"] = sum(components.values())
    row["quality_label"] = int(row["quality_score"] >= 80)
    row["quality_level"] = "High" if row["quality_label"] else ("Medium" if row["quality_score"] >= 60 else "Low")
    return row


def _missing_counts(rows: Sequence[Dict[str, Any]], fields: Sequence[str]) -> Dict[str, int]:
    return {field: sum(not normalize_whitespace(row.get(field, "")) for row in rows) for field in fields}


def _quantile(values: Sequence[float], probability: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def apply_usd_winsorization(rows: Sequence[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    values = [
        float(row["salary_avg_annual"])
        for row in rows
        if row.get("salary_currency") == "USD"
        and row.get("salary_avg_annual") is not None
        and not row.get("salary_outlier")
    ]
    lower, upper = _quantile(values, 0.01), _quantile(values, 0.99)
    for row in rows:
        value = row.get("salary_avg_annual")
        if row.get("salary_currency") == "USD" and value is not None and not row.get("salary_outlier") and lower is not None and upper is not None:
            row["salary_avg_usd_annual_winsorized"] = min(max(float(value), lower), upper)
        else:
            row["salary_avg_usd_annual_winsorized"] = None
    return {"usd_p01": lower, "usd_p99": upper}


def write_jsonl(rows: Iterable[Dict[str, Any]], path: Path) -> None:
    ensure_derived_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_teacher_csv(rows: Sequence[Dict[str, Any]], path: Path) -> None:
    ensure_derived_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    excluded = {"description_tokens", "description_clean"}
    source_empty_fields = {"education", "industry", "company_type", "company_size", "longitude", "latitude"}
    fields = [
        field
        for field in rows[0]
        if field not in excluded and field not in source_empty_fields
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_audit(
    raw_rows: Sequence[Dict[str, Any]],
    cleaned_rows: Sequence[Dict[str, Any]],
    duplicates: Sequence[Dict[str, Any]],
    files: Sequence[Path],
    winsor: Dict[str, Optional[float]],
) -> Dict[str, Any]:
    labels = Counter(row["quality_level"] for row in cleaned_rows)
    salary_status = Counter(row["salary_parse_status"] for row in cleaned_rows)
    experience_status = Counter(row["experience_parse_status"] for row in cleaned_rows)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_directory": str(DEFAULT_INPUT_DIR.relative_to(PROJECT_ROOT)),
        "source_file_pattern": "remote_all_*.jsonl",
        "historical_aggregate_excluded": "data/raw/jobs_all.jsonl",
        "source_file_count": len(files),
        "raw_record_count": len(raw_rows),
        "deduplicated_record_count": len(cleaned_rows),
        "duplicate_count": len(duplicates),
        "duplicate_rate": len(duplicates) / len(raw_rows) if raw_rows else 0,
        "dedupe_precedence": ["source + job_id", "source_url", "title + company + city + salary + publish_date"],
        "missing_before": _missing_counts(raw_rows, EXPECTED_SOURCE_FIELDS),
        "missing_after": _missing_counts(cleaned_rows, EXPECTED_SOURCE_FIELDS),
        "field_types_before": {
            field: sorted({type(row.get(field)).__name__ for row in raw_rows})
            for field in EXPECTED_SOURCE_FIELDS
        },
        "salary_parse_status": dict(salary_status),
        "salary_outlier_count": sum(bool(row["salary_outlier"]) for row in cleaned_rows),
        "experience_parse_status": dict(experience_status),
        "quality_level_distribution": dict(labels),
        "quality_label_definition": "quality_label=1 when deterministic information-quality score >= 80/100",
        "winsorization": winsor,
        "invariants": {
            "all_city_remote": all(row["city"] == "Remote" for row in cleaned_rows),
            "all_trace_fields_present": all(all(row.get(field) for field in TRACE_FIELDS) for row in cleaned_rows),
            "effective_records_at_least_10000": len(cleaned_rows) >= 10_000,
        },
    }


def write_quality_markdown(audit: Dict[str, Any], path: Path) -> None:
    ensure_derived_output(path)
    missing = audit["missing_before"]
    total = audit["raw_record_count"]
    source_empty_fields = [field for field, count in missing.items() if count == total]
    report_fields = [field for field, count in missing.items() if count < total]
    rows = "\n".join(
        f"| `{field}` | {', '.join(audit['field_types_before'][field])} | {count:,} | {count / total:.1%} |"
        for field, count in missing.items()
        if field in report_fields
    )
    invariants = "\n".join(
        f"- {'通过' if passed else '未通过'}：`{name}`"
        for name, passed in audit["invariants"].items()
    )
    text = f"""# 数据质量报告

生成时间：{audit['generated_at']}

## 数据范围

- 唯一输入：`{audit['source_directory']}/remote_all_*.jsonl`
- 分页文件：{audit['source_file_count']:,} 个
- 原始记录：{audit['raw_record_count']:,} 条
- 去重后记录：{audit['deduplicated_record_count']:,} 条
- 重复记录：{audit['duplicate_count']:,} 条（{audit['duplicate_rate']:.2%}）
- 明确排除历史聚合文件：`{audit['historical_aggregate_excluded']}`

## 去重规则

按以下优先级保留首次出现记录：`source + job_id`、`source_url`、业务字段组合（岗位名、公司、城市、原始薪资、发布日期）。重复明细单独输出，不修改来源文件。

## 关键字段缺失

| 字段 | 原始类型 | 缺失数 | 缺失率 |
|---|---|---:|---:|
{rows}

来源 API 未提供的字段（`{'、'.join(source_empty_fields)}）不列入上表，也不进入当前模型与图表；完整字段统计仍保留在 `data_quality_summary.json`。这些字段不做虚构填充。`salary_raw` 缺失也保留缺失标记。

## 解析与异常处理

- 薪资：解析币种、周期和上下限；年薪化系数为 hourly×2080、daily×260、weekly×52、monthly×12、annual×1。
- 跨币种：不使用外部汇率，不直接比较不同币种；图表和建模中的金额只采用 USD 年薪化字段。
- 异常值：年薪化小于 5,000 或大于 1,000,000，或上下限倒置，标记为异常但不覆盖原值。
- 薪资异常标记：{audit['salary_outlier_count']:,} 条。
- 稳健分析值：对非异常 USD 年薪按样本内 P1/P99 缩尾，边界为 {audit['winsorization']['usd_p01']:,.2f} / {audit['winsorization']['usd_p99']:,.2f} USD。
- 经验：来源职级映射为经验年限区间；该字段是分析代理，不是雇主明确要求年限。
- 文本：统一大小写和空白，移除 URL 与标点，使用 jieba 分词并过滤基础停用词。

## 验收检查

{invariants}

## 标签说明

岗位质量分衡量的是“招聘信息透明度与完整度”，不是企业好坏、真实工作体验或录用概率。高质量标签为固定规则分数达到 80/100，供课程模型复现规则使用，不宣称是人工真实标签。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_preprocessing_doc(audit: Dict[str, Any], path: Path) -> None:
    ensure_derived_output(path)
    total = audit["deduplicated_record_count"]
    label_dist = audit["quality_level_distribution"]
    text = f"""# 数据预处理文档

## 1. 处理目标与边界

本流程只读取 `data/raw/himalayas_api/2026-09-08/` 下 600 个 `remote_all_*.jsonl` 分页文件。`data/raw/jobs_all.jsonl` 是历史聚合文件，明确排除。原始 JSONL 和 API 响应不修改、不覆盖、不删除，所有结果写入 `data/processed/`、`export/`、`reports/` 或 `docs/`。

数据研究对象为全球远程岗位，`city=Remote` 保持来源语义；`district` 表示岗位允许申请的国家或地区限制。

## 2. 合并与去重

- 合并前：{audit['raw_record_count']:,} 条，{audit['source_file_count']} 个分页文件。
- 去重后：{total:,} 条。
- 重复：{audit['duplicate_count']:,} 条，重复率 {audit['duplicate_rate']:.2%}。
- 去重键依次为 `source + job_id`、`source_url`、岗位名/公司/城市/薪资/发布日期组合。
- 每条结果保留 `source_url`、`crawl_time`、`data_origin`，并增加 `raw_page_file` 和 `raw_line_number` 便于回溯。

## 3. 缺失值

不把“未提供”伪造成业务值。文本字段保留空字符串，数值解析字段保留空值，并添加 `salary_parse_status`、`experience_parse_status` 等状态字段。来源 API 未提供的学历、行业、公司性质、公司规模和经纬度保持为空。薪资缺失不以 0 填充。

## 4. 字段标准化与特征工程

| 新字段 | 含义 |
|---|---|
| `salary_currency`, `salary_period` | 薪资币种与周期 |
| `salary_min`, `salary_max`, `salary_avg` | 原周期数值薪资 |
| `salary_*_annual` | 按固定工时假设年薪化后的同币种薪资 |
| `salary_avg_usd_annual_winsorized` | 仅 USD 非异常记录的 P1/P99 缩尾值 |
| `experience_year_min/max` | 职级映射得到的经验区间代理 |
| `is_fresh_graduate` | 是否包含 Entry-level 的代理标记 |
| `description_clean/tokens` | 清洗文本与 jieba 分词结果 |
| `description_length/word_count` | 描述字符数和英文空格词数 |
| `description_structure_count` | 职责、要求、福利等结构提示词命中数 |
| `skills_normalized`, `skill_count` | 规范化技能和技能数量 |
| `broad_category` | 按固定关键词映射的宽类岗位类别 |
| `is_it_data_role` | 工程或数据科学岗位标记 |
| `quality_score/label/level` | 信息质量规则分、二分类标签和展示等级 |

## 5. 薪资与异常值

薪资周期统一采用 annual×1、monthly×12、weekly×52、daily×260、hourly×2080。这个换算只用于统计比较，未考虑奖金、股权、工时差异和税制。不同币种不做汇率换算。年薪化低于 5,000 或高于 1,000,000，以及上下限倒置的记录只打标，不删除；USD 分析值进一步按 P1/P99 缩尾。

## 6. 岗位信息质量标签

总分 100 分：追溯字段 5、核心字段 10、地点限制 5、描述完整性 25、薪资透明度 15、技能清晰度 20、职级 10、时效性 5、类别 5。描述长度和技能数采用分段递增并设上限，防止单一“是/否”字段决定标签。`quality_score >= 80` 定义为高信息质量。当前分布为 High {label_dist.get('High', 0):,}、Medium {label_dist.get('Medium', 0):,}、Low {label_dist.get('Low', 0):,}。

该标签是可复现的课程代理标签。它衡量岗位信息是否完整透明，不代表雇主信誉、工作体验、薪酬竞争力或候选人最终录用概率。后续应通过人工抽样标注或求职结果反馈建立外部效度。

## 7. 可复现命令

```bash
PYTHONPATH=src .venv/bin/python -m job_analysis.cleaning --sample-size 200
PYTHONPATH=src .venv/bin/python -m job_analysis.cleaning
```

样本命令只生成 `data/processed/sample_validation/` 下的验证结果；全量命令生成正式数据和报告。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_parquet(rows: Sequence[Dict[str, Any]], path: Path) -> None:
    ensure_derived_output(path)
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def run(input_dir: Path, output_root: Path, sample_size: Optional[int] = None) -> Dict[str, Any]:
    files = source_files(input_dir)
    if not sample_size and len(files) != 600:
        raise ValueError(f"Expected 600 source page files, found {len(files)}")
    raw_rows = load_source_records(input_dir)
    if sample_size:
        raw_rows = raw_rows[:sample_size]
    elif len(raw_rows) != 12_000:
        raise ValueError(f"Expected 12,000 raw records, found {len(raw_rows)}")
    unique_rows, duplicates = deduplicate_records(raw_rows)
    reference_time = max(
        (parse_iso_datetime(row.get("crawl_time")) for row in unique_rows if parse_iso_datetime(row.get("crawl_time"))),
        default=datetime(2026, 9, 8, tzinfo=timezone.utc),
    )
    cleaned_rows = [clean_record(row, reference_time) for row in unique_rows]
    winsor = apply_usd_winsorization(cleaned_rows)
    audit = build_audit(raw_rows, cleaned_rows, duplicates, files, winsor)

    processed_dir = output_root / "data/processed"
    export_dir = output_root / "export"
    reports_dir = output_root / "reports"
    docs_dir = output_root / "docs"
    if sample_size:
        processed_dir = processed_dir / "sample_validation"
        export_dir = export_dir / "sample_validation"
        reports_dir = reports_dir / "sample_validation"
        docs_dir = docs_dir / "sample_validation"

    write_jsonl(unique_rows, processed_dir / "jobs_merged_deduplicated.jsonl")
    write_jsonl(duplicates, processed_dir / "duplicate_records.jsonl")
    write_parquet(cleaned_rows, processed_dir / "jobs_cleaned.parquet")
    write_teacher_csv(cleaned_rows, export_dir / "jobs_cleaned_teacher.csv")
    write_jsonl(cleaned_rows, processed_dir / "jobs_cleaned.jsonl")
    audit_path = reports_dir / "data_quality_summary.json"
    ensure_derived_output(audit_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_quality_markdown(audit, reports_dir / "data_quality_report.md")
    write_preprocessing_doc(audit, docs_dir / "data_preprocessing.md")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and engineer features for the authorized Himalayas job dataset")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--sample-size", type=int)
    args = parser.parse_args()
    audit = run(args.input_dir, args.output_root, args.sample_size)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
