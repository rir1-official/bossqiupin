import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .extract import extract_items, get_path, normalize_item
from .http_client import AccessBlocked, PublicHttpClient, render_url
from .models import JobRecord, REQUIRED_FIELDS
from .storage import append_log, read_jsonl, write_page, write_response


def crawl(config: Dict, max_pages: Optional[int] = None, raw_root: str = "data/raw") -> Dict[str, int]:
    settings = config["request"]
    client = PublicHttpClient(settings)
    stats = {"pages_ok": 0, "pages_failed": 0, "records": 0}
    for source in config["sources"]:
        if not source.get("enabled", False):
            continue
        if source.get("format") != "json":
            raise ValueError(f"当前版本仅支持 json 来源: {source['name']}")
        for city in config["targets"]["cities"]:
            for keyword in config["targets"]["keywords"]:
                limit = min(int(source.get("max_pages", 999999)), max_pages or 999999)
                for page in range(1, limit + 1):
                    url = render_url(source["list_url_template"], city, keyword, page)
                    try:
                        payload, raw_response = client.get_json_with_raw(url)
                        raw_items = extract_items(payload, source["items_path"])
                        if not raw_items:
                            break
                        write_response(raw_response, source["name"], city, keyword, page)
                        now = datetime.now(timezone.utc).isoformat()
                        records = []
                        for item in raw_items:
                            values = normalize_item(item, source["field_map"], source["name"], city)
                            detail_template = source.get("detail_url_template")
                            detail_id_path = source.get("detail_id_path")
                            if detail_template and detail_id_path:
                                detail_id = get_path(item, detail_id_path)
                                if detail_id:
                                    detail_url = detail_template.format(id=detail_id)
                                    detail_payload, _ = client.get_json_with_raw(detail_url)
                                    for field, path in source.get("detail_field_map", {}).items():
                                        value = get_path(detail_payload, path)
                                        values[field] = ",".join(map(str, value)) if isinstance(value, list) else value
                                    values["source_url"] = values.get("source_url") or detail_url
                            values["crawl_time"] = now
                            values["data_origin"] = "self_crawled"
                            record = JobRecord.from_dict(values).to_dict()
                            records.append(record)
                        write_page(records, source["name"], city, keyword, page, raw_root)
                        append_log({"time": now, "source": source["name"], "city": city, "keyword": keyword, "page": page, "status": "ok", "records": len(records), "message": url})
                        stats["pages_ok"] += 1
                        stats["records"] += len(records)
                    except AccessBlocked as exc:
                        append_log({"time": datetime.now(timezone.utc).isoformat(), "source": source["name"], "city": city, "keyword": keyword, "page": page, "status": "blocked", "records": 0, "message": str(exc)})
                        stats["pages_failed"] += 1
                        break
                    except Exception as exc:
                        append_log({"time": datetime.now(timezone.utc).isoformat(), "source": source["name"], "city": city, "keyword": keyword, "page": page, "status": "failed", "records": 0, "message": str(exc)})
                        stats["pages_failed"] += 1
                        break
                time.sleep(random.uniform(settings["keyword_pause_min_seconds"], settings["keyword_pause_max_seconds"]))
    return stats


def dedupe_key(record: Dict) -> Tuple[str, ...]:
    source = str(record.get("source", "")).strip()
    job_id = str(record.get("job_id", "")).strip()
    if source and job_id:
        return ("id", source, job_id)
    return ("fallback", *(str(record.get(field, "")).strip().lower() for field in ("job_title", "company_name", "city", "salary_raw", "publish_date")))


def merge_and_dedupe(raw_dir: str, output: str) -> Dict[str, int]:
    records, seen = 0, set()
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for path in Path(raw_dir).rglob("*.jsonl"):
            if path.resolve() == destination.resolve():
                continue
            for record in read_jsonl(path):
                records += 1
                key = dedupe_key(record)
                if key in seen:
                    continue
                seen.add(key)
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"raw_records": records, "deduped_records": len(seen), "duplicates": records - len(seen)}


def quality_summary(input_path: str) -> Dict:
    rows = list(read_jsonl(Path(input_path)))
    total = len(rows)
    completeness = {field: (sum(bool(str(row.get(field, "")).strip()) for row in rows) / total if total else 0) for field in REQUIRED_FIELDS}
    salary_or_description = sum(bool(str(row.get("salary_raw", "")).strip() or str(row.get("job_description", "")).strip()) for row in rows) / total if total else 0
    cities, titles = {}, {}
    for row in rows:
        cities[row.get("city", "未知")] = cities.get(row.get("city", "未知"), 0) + 1
        titles[row.get("job_title", "未知")] = titles.get(row.get("job_title", "未知"), 0) + 1
    return {"total": total, "completeness": completeness, "salary_or_description": salary_or_description, "city_distribution": cities, "top_job_titles": dict(sorted(titles.items(), key=lambda item: item[1], reverse=True)[:20])}


def write_quality_report(summary: Dict, output: str) -> None:
    criteria = {
        "岗位名称、城市、来源链接完整率 >= 95%": all(summary["completeness"].get(field, 0) >= 0.95 for field in ("job_title", "city", "source_url")),
        "薪资或岗位描述完整率 >= 85%": summary["salary_or_description"] >= 0.85,
        "去重后有效记录 >= 10,000": summary["total"] >= 10000,
    }
    lines = ["# 数据采集质量报告", "", f"- 有效岗位记录：{summary['total']}", f"- 薪资或岗位描述完整率：{summary['salary_or_description']:.2%}", "", "## 核心字段完整率", ""]
    lines += [f"- {field}：{rate:.2%}" for field, rate in summary["completeness"].items()]
    lines += ["", "## 城市分布", ""] + [f"- {city}：{count}" for city, count in sorted(summary["city_distribution"].items())]
    lines += ["", "## 验收判断", ""] + [f"- {'通过' if passed else '未通过'}：{name}" for name, passed in criteria.items()]
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text("\n".join(lines) + "\n", encoding="utf-8")
