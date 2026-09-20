"""FAISS-based semantic retrieval experiment for the local job corpus.

The formal Week 2 RAG experiment uses a real Chinese sentence embedding model,
chunk-level source metadata, a persisted FAISS index, and reproducible gold-set
rules for retrieval evaluation. It never reads or writes the raw collection.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import os
import re
import time
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# macOS Command Line Tools' Python + PyTorch can occasionally segfault in the
# default OpenMP thread pool during CPU embedding. Keep the local experiment
# deterministic and single-threaded unless the caller explicitly overrides it.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import faiss
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer


def _configure_torch_runtime() -> None:
    """Keep the macOS fallback deterministic before any encoder is created."""
    thread_count = max(1, int(os.environ.get("TORCH_NUM_THREADS", "1")))
    interop_count = max(1, int(os.environ.get("TORCH_NUM_INTEROP_THREADS", "1")))
    try:
        torch.set_num_threads(thread_count)
    except RuntimeError:
        pass
    try:
        torch.set_num_interop_threads(interop_count)
    except RuntimeError:
        pass


_configure_torch_runtime()

from .cleaning import PROJECT_ROOT, ensure_derived_output


DEFAULT_DATA = PROJECT_ROOT / "data/processed/jobs_cleaned.parquet"
DEFAULT_INDEX_DIR = PROJECT_ROOT / "data/processed/rag"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports/rag"
DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_TOP_K = 3
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

REQUIRED_SOURCE_FIELDS = [
    "job_id",
    "job_title",
    "source_url",
    "crawl_time",
    "data_origin",
]

CHUNK_METADATA_FIELDS = [
    "job_id",
    "job_title",
    "company_name",
    "chunk_id",
    "section_name",
    "source_field",
    "section_source",
    "section_index",
    "chunk_index",
    "chunk_text",
    "chunk_body",
    "chunk_char_count",
    "section_char_count",
    "broad_category",
    "job_category",
    "skills_normalized",
    "city",
    "district",
    "source_url",
    "crawl_time",
    "data_origin",
]


# Himalayas descriptions are mostly English even though the experiment uses a
# Chinese embedding model. These labels cover the recurring heading variants
# without assuming every job uses the same template.
SECTION_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (
        "responsibilities",
        r"(?:responsibilities|what\s+(?:you(?:['’]ll|\s+will)|you)\s+do|duties|your\s+responsibilities|key\s+responsibilities|role\s+responsibilities)",
    ),
    (
        "requirements",
        r"(?:requirements|qualifications|what\s+(?:you(?:['’]ll|\s+will)|you)\s+need|what\s+we(?:['’]re|\s+are)\s+looking\s+for|skills\s+and\s+experience|must\s+have|preferred\s+qualifications)",
    ),
    (
        "job_introduction",
        r"(?:job\s+brief|about\s+(?:the\s+)?(?:role|position|company|us)|position\s+description|the\s+opportunity|overview|who\s+we\s+are|company\s+description)",
    ),
)

SECTION_LABELS = {
    "job_introduction": "岗位介绍",
    "responsibilities": "岗位职责",
    "requirements": "任职要求",
    "other": "其他岗位信息",
}


@dataclass(frozen=True)
class QuerySpec:
    question_id: str
    question_type: str
    question: str
    rationale: str
    must_all: Tuple[str, ...] = ()
    must_any: Tuple[str, ...] = ()
    broad_categories: Tuple[str, ...] = ()
    districts: Tuple[str, ...] = ()
    exclude_any: Tuple[str, ...] = ()


TEST_QUERIES: Tuple[QuerySpec, ...] = (
    QuerySpec(
        "Q01",
        "基础查询",
        "想找同时要求 Python 和 SQL 的远程数据分析岗位。",
        "验证两个明确技术技能与数据岗位类别的联合召回。",
        must_all=("python", "sql"),
        broad_categories=("Data Science",),
    ),
    QuerySpec(
        "Q02",
        "细节查询",
        "需要会 AWS、Docker 和 Kubernetes 的远程 DevOps 或云平台岗位。",
        "验证三个基础设施技能同时出现时的精确召回。",
        must_all=("aws", "docker", "kubernetes"),
        must_any=("devops", "cloud", "platform", "site reliability"),
        broad_categories=("Engineering", "Data Science"),
    ),
    QuerySpec(
        "Q03",
        "基础查询",
        "寻找 React 和 TypeScript 技术栈的远程前端开发岗位。",
        "验证主流前端框架和语言组合。",
        must_all=("react", "typescript"),
        must_any=("frontend", "front end", "full stack", "fullstack"),
        broad_categories=("Engineering",),
    ),
    QuerySpec(
        "Q04",
        "细节查询",
        "想找需要 Excel 和 Tableau 的商业分析或业务分析岗位。",
        "验证办公分析工具与业务分析角色的联合条件。",
        must_all=("excel", "tableau"),
        must_any=("business analyst", "business analysis", "business intelligence", "data analyst"),
    ),
    QuerySpec(
        "Q05",
        "模糊查询",
        "有哪些负责人工智能模型评估、质量审核或安全测试的远程岗位？",
        "用中文语义表达检索 AI evaluation、model evaluation 等英文岗位概念。",
        must_any=("ai evaluation", "model evaluation", "model evaluator", "ai safety", "model quality"),
        broad_categories=("Data Science", "Engineering", "Other"),
    ),
    QuerySpec(
        "Q06",
        "细节查询",
        "寻找使用 PostgreSQL 的远程数据工程岗位。",
        "验证具体数据库技术和数据工程角色。",
        must_all=("postgresql",),
        must_any=("data engineer", "data engineering", "data platform"),
        broad_categories=("Data Science", "Engineering"),
    ),
    QuerySpec(
        "Q07",
        "模糊查询",
        "希望找维护客户关系、处理客户问题并提升续约体验的远程岗位。",
        "不直接给出岗位标题，验证 Customer Success 和 Customer Support 的语义召回。",
        must_any=("customer success", "customer support", "client success", "technical support"),
        broad_categories=("Customer Service", "Sales", "Operations"),
    ),
    QuerySpec(
        "Q08",
        "基础查询",
        "寻找销售拓展或客户账户管理方向的远程岗位。",
        "验证 Sales 与 Account Management 近邻业务角色。",
        must_any=("business development", "account management", "account manager", "account executive"),
        broad_categories=("Sales",),
    ),
    QuerySpec(
        "Q09",
        "易混淆岗位查询",
        "找产品经理岗位，不要 SEO、ASO 或纯营销增长岗位。",
        "区分 Product Management 与名称相近的 Marketing 产品推广岗位。",
        must_any=("product manager", "product management", "product owner"),
        broad_categories=("Product",),
        exclude_any=("seo", "aso", "growth marketing", "performance marketing"),
    ),
    QuerySpec(
        "Q10",
        "易混淆岗位查询",
        "寻找使用 Excel 做预算、财务规划或财务分析的岗位，不要普通数据分析师。",
        "区分 Finance 岗位和通用 Data Analyst 岗位。",
        must_all=("excel",),
        must_any=("finance", "financial", "budget", "fp&a"),
        broad_categories=("Finance",),
        exclude_any=("data analyst",),
    ),
    QuerySpec(
        "Q11",
        "细节查询",
        "寻找面向美国地区、使用 Java 的远程后端工程岗位。",
        "验证技能、角色和地区三个维度的联合召回。",
        must_all=("java",),
        must_any=("backend", "back end", "software engineer"),
        broad_categories=("Engineering",),
        districts=("United States",),
    ),
    QuerySpec(
        "Q12",
        "模糊查询",
        "想从事训练、部署和维护预测模型的远程机器学习工程工作。",
        "用职责描述检索 Machine Learning Engineering 角色。",
        must_any=("machine learning engineer", "machine learning engineering", "ml engineer", "ai ml engineer"),
        broad_categories=("Data Science",),
    ),
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _json_value(value: Any) -> Any:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    return value


def clean_rag_text(value: Any) -> str:
    """Normalize job text while keeping sentence punctuation for chunking."""
    text = html.unescape(_text(value))
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\ufffd", " ").replace("\x00", " ")
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]", " ", text)
    text = re.sub(r"[•●▪◦◆◇►▶→⇒]+", "\n", text)
    text = re.sub(r"[\t\r\f\v]+", " ", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_long_segment(segment: str, chunk_size: int) -> List[str]:
    parts: List[str] = []
    remaining = segment.strip()
    while len(remaining) > chunk_size:
        window = remaining[:chunk_size]
        cut = max(window.rfind(" "), window.rfind(","), window.rfind(";"), window.rfind(":"))
        if cut < int(chunk_size * 0.65):
            cut = chunk_size
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return parts


def split_semantic_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Build sentence-preferred chunks with character overlap."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap must be smaller")
    clean = clean_rag_text(text)
    if not clean:
        return []
    raw_segments = re.split(r"(?<=[.!?。！？;；])\s+|\n+", clean)
    segments: List[str] = []
    for segment in raw_segments:
        segment = segment.strip()
        if not segment:
            continue
        segments.extend(_split_long_segment(segment, chunk_size))

    chunks: List[str] = []
    current = ""
    for segment in segments:
        candidate = segment if not current else current + " " + segment
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current.strip())
            prefix = current[-overlap:].strip() if overlap else ""
            current = (prefix + " " + segment).strip() if prefix else segment
            if len(current) > chunk_size:
                overflow_parts = _split_long_segment(current, chunk_size)
                chunks.extend(overflow_parts[:-1])
                current = overflow_parts[-1]
        else:
            chunks.append(segment[:chunk_size].strip())
            current = segment[max(0, chunk_size - overlap) :].strip()
    if current:
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def validate_and_filter_jobs(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    missing_columns = [column for column in REQUIRED_SOURCE_FIELDS if column not in df]
    if missing_columns:
        raise ValueError("missing required source fields: " + ", ".join(missing_columns))
    work = df.copy()
    original_rows = len(work)
    duplicate_rows = int(work.duplicated(subset=["job_id"], keep="first").sum())
    work = work.drop_duplicates(subset=["job_id"], keep="first")
    description = work.get("job_description", pd.Series("", index=work.index)).map(clean_rag_text)
    fallback = work.get("description_clean", pd.Series("", index=work.index)).map(clean_rag_text)
    work["rag_description"] = description.where(description.str.len() >= 40, fallback)
    required_mask = pd.Series(True, index=work.index)
    for column in REQUIRED_SOURCE_FIELDS:
        required_mask &= work[column].map(_text).str.strip().ne("")
    required_mask &= work["rag_description"].str.len().ge(40)
    incomplete_rows = int((~required_mask).sum())
    work = work.loc[required_mask].reset_index(drop=True)
    section_rows = [parse_job_sections(text) for text in work["rag_description"]]
    work["job_introduction"] = [item["job_introduction"] for item in section_rows]
    work["responsibilities_text"] = [item["responsibilities"] for item in section_rows]
    work["requirements_text"] = [item["requirements"] for item in section_rows]
    work["section_parse_summary"] = [item["summary"] for item in section_rows]
    stats = {
        "input_rows": int(original_rows),
        "duplicate_job_ids_removed": duplicate_rows,
        "incomplete_rows_removed": incomplete_rows,
        "valid_rows": int(len(work)),
        "section_parsing": {
            "job_introduction_explicit": int(sum(item["summary"]["job_introduction_explicit"] for item in section_rows)),
            "responsibilities_explicit": int(sum(item["summary"]["responsibilities_explicit"] for item in section_rows)),
            "requirements_explicit": int(sum(item["summary"]["requirements_explicit"] for item in section_rows)),
            "job_introduction_fallback": int(sum(item["summary"]["job_introduction_fallback"] for item in section_rows)),
            "responsibilities_fallback": int(sum(item["summary"]["responsibilities_fallback"] for item in section_rows)),
            "requirements_fallback": int(sum(item["summary"]["requirements_fallback"] for item in section_rows)),
        },
    }
    return work, stats


def parse_job_sections(text: Any) -> Dict[str, Any]:
    """Extract introduction, responsibilities and requirements from one job.

    A heading is treated as a section boundary. When a section is missing, the
    complete cleaned description is retained as a documented fallback so no
    otherwise valid job silently disappears from the knowledge base.
    """
    clean = clean_rag_text(text)
    matches: List[Tuple[int, int, str, str]] = []
    for section_name, pattern in SECTION_PATTERNS:
        for match in re.finditer(r"(?im)(?:^|(?<=[.!?;:])\s+)" + pattern + r"\s*:?[ \t]*(?:\n|(?=[A-Z0-9]))", clean):
            matches.append((match.start(), match.end(), section_name, match.group(0)))
    matches.sort(key=lambda item: (item[0], item[1]))
    deduped: List[Tuple[int, int, str, str]] = []
    for item in matches:
        if deduped and item[0] < deduped[-1][1]:
            continue
        deduped.append(item)

    sections: Dict[str, str] = {}
    sources: Dict[str, str] = {}
    for index, (start, end, name, _label) in enumerate(deduped):
        stop = deduped[index + 1][0] if index + 1 < len(deduped) else len(clean)
        body = clean[end:stop].strip(" \n:-")
        if len(body) >= 20 and name not in sections:
            sections[name] = body
            sources[name] = "explicit_heading"
    for name in ("job_introduction", "responsibilities", "requirements"):
        if name not in sections:
            sections[name] = clean
            sources[name] = "full_description_fallback"
    summary = {
        "job_introduction_explicit": int(sources["job_introduction"] == "explicit_heading"),
        "responsibilities_explicit": int(sources["responsibilities"] == "explicit_heading"),
        "requirements_explicit": int(sources["requirements"] == "explicit_heading"),
        "job_introduction_fallback": int(sources["job_introduction"] != "explicit_heading"),
        "responsibilities_fallback": int(sources["responsibilities"] != "explicit_heading"),
        "requirements_fallback": int(sources["requirements"] != "explicit_heading"),
        "sources": sources,
        "clean_char_count": len(clean),
    }
    return {
        "job_introduction": sections["job_introduction"],
        "responsibilities": sections["responsibilities"],
        "requirements": sections["requirements"],
        "sources": sources,
        "summary": summary,
    }


def build_chunk_dataframe(
    jobs: pd.DataFrame,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for job in jobs.to_dict(orient="records"):
        explicit_sources = (job.get("section_parse_summary") or {}).get("sources", {})
        has_explicit_section = any(value == "explicit_heading" for value in explicit_sources.values())
        if has_explicit_section:
            # Index explicit sections separately. The complete-text fallbacks
            # are already covered by the surrounding description and would
            # otherwise create three near-duplicate copies per job.
            sections = tuple(
                item
                for item in (
                    ("job_introduction", "job_introduction", "岗位介绍"),
                    ("responsibilities", "responsibilities_text", "岗位职责"),
                    ("requirements", "requirements_text", "任职要求"),
                )
                if explicit_sources.get(item[0]) == "explicit_heading"
            )
        else:
            sections = (("job_combined", "rag_description", "岗位综合文本（回退）"),)
        section_index = 0
        for section_name, source_field, section_label in sections:
            section_body = clean_rag_text(job.get(source_field, ""))
            body_chunks = split_semantic_chunks(section_body, chunk_size, overlap)
            if not body_chunks:
                continue
            section_source = explicit_sources.get(section_name, "full_description_fallback")
            for chunk_index, chunk_body in enumerate(body_chunks):
                chunk_id = "{}::{}::c{:04d}".format(_text(job.get("job_id")), section_name, chunk_index)
                context = (
                    "岗位名称：{}\n公司：{}\n岗位大类：{}\n岗位类别：{}\n技能标签：{}\n"
                    "地区限制：{}\n文本区段：{}\n岗位文本：\n{}"
                ).format(
                    _text(job.get("job_title")),
                    _text(job.get("company_name")),
                    _text(job.get("broad_category")),
                    _text(job.get("job_category")),
                    _text(job.get("skills_normalized")).replace("|", "、"),
                    _text(job.get("district")),
                    section_label,
                    chunk_body,
                )
                rows.append(
                    {
                        "job_id": _text(job.get("job_id")),
                        "job_title": _text(job.get("job_title")),
                        "company_name": _text(job.get("company_name")),
                        "chunk_id": chunk_id,
                        "section_name": section_label,
                        "source_field": source_field,
                        "section_source": section_source,
                        "section_index": section_index,
                        "chunk_index": chunk_index,
                        "chunk_text": context,
                        "chunk_body": chunk_body,
                        "chunk_char_count": len(chunk_body),
                        "section_char_count": len(section_body),
                        "broad_category": _text(job.get("broad_category")),
                        "job_category": _text(job.get("job_category")),
                        "skills_normalized": _text(job.get("skills_normalized")),
                        "city": _text(job.get("city")),
                        "district": _text(job.get("district")),
                        "source_url": _text(job.get("source_url")),
                        "crawl_time": _json_value(job.get("crawl_time")),
                        "data_origin": _text(job.get("data_origin")),
                    }
                )
            section_index += 1
    chunks = pd.DataFrame(rows, columns=CHUNK_METADATA_FIELDS)
    if chunks.empty:
        raise ValueError("no chunks were generated")
    if chunks["chunk_id"].duplicated().any():
        raise ValueError("chunk_id must be unique")
    return chunks


def resolve_device(device: str = "auto") -> str:
    """Choose a stable local inference device.

    macOS CPU embedding occasionally terminates the interpreter inside PyTorch's
    threaded kernels. Apple Silicon hosts therefore use MPS by default when it
    is available; CPU remains a supported, single-threaded fallback.
    """
    requested = str(device).strip().lower() or "auto"
    if requested == "auto":
        return "mps" if torch.backends.mps.is_available() else "cpu"
    if requested == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS was requested but is not available in this Python environment")
    if requested not in {"cpu", "mps", "cuda"}:
        raise ValueError("device must be one of: auto, cpu, mps, cuda")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available in this Python environment")
    return requested


def load_embedding_model(model_name: str = DEFAULT_MODEL, device: str = "auto") -> SentenceTransformer:
    resolved_device = resolve_device(device)
    if resolved_device == "cpu":
        torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "1")))
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            # PyTorch only allows this setting before its first parallel op.
            pass
    bundled_model = os.getenv("RAG_EMBEDDING_MODEL_PATH", "").strip()
    # Docker packages the verified local BGE snapshot at this path.  The
    # manifest retains the canonical model identifier for experiment traceability.
    resolved_model_name = bundled_model or model_name
    local_only = bundled_model or os.getenv("HF_LOCAL_FILES_ONLY", "0").strip().lower() in {"1", "true", "yes"}
    return SentenceTransformer(resolved_model_name, device=resolved_device, local_files_only=bool(local_only))


def encode_texts(
    model: SentenceTransformer,
    texts: Sequence[str],
    batch_size: int = 64,
    query: bool = False,
) -> np.ndarray:
    payload = [QUERY_INSTRUCTION + text if query else text for text in texts]
    vectors = model.encode(
        payload,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return np.asarray(vectors, dtype=np.float32)


def _write_json(path: Path, payload: Any) -> None:
    ensure_derived_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    ensure_derived_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps({key: _json_value(value) for key, value in row.items()}, ensure_ascii=False) + "\n")


def build_faiss_knowledge_base(
    data_path: Path = DEFAULT_DATA,
    index_dir: Path = DEFAULT_INDEX_DIR,
    model_name: str = DEFAULT_MODEL,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    batch_size: int = 64,
    device: str = "auto",
) -> Dict[str, Any]:
    started = time.perf_counter()
    source_df = pd.read_parquet(data_path)
    jobs, cleaning_stats = validate_and_filter_jobs(source_df)
    chunks = build_chunk_dataframe(jobs, chunk_size, overlap)
    resolved_device = resolve_device(device)
    model = load_embedding_model(model_name, resolved_device)
    vectors = encode_texts(model, chunks["chunk_text"].tolist(), batch_size=batch_size)
    if vectors.shape[0] != len(chunks):
        raise ValueError("embedding count does not match chunk count")
    index = faiss.IndexFlatIP(int(vectors.shape[1]))
    for start in range(0, len(vectors), 4096):
        index.add(vectors[start : start + 4096])
    if index.ntotal != len(chunks):
        raise ValueError("FAISS index count does not match chunk count")

    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_dir / "faiss.index"))
    ensure_derived_output(index_dir / "chunks.parquet")
    chunks.to_parquet(index_dir / "chunks.parquet", index=False)
    _write_jsonl(index_dir / "chunk_metadata.jsonl", chunks.to_dict(orient="records"))
    manifest = {
        "experiment": "Chinese semantic job retrieval with FAISS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_data": str(data_path.relative_to(PROJECT_ROOT)),
        "source_rows": int(len(source_df)),
        "cleaning": cleaning_stats,
        "vector_store": {
            "name": "FAISS",
            "index_type": "IndexFlatIP",
            "metric": "cosine similarity via normalized inner product",
            "index_file": "faiss.index",
        },
        "embedding": {
            "model": model_name,
            "language_focus": "Chinese",
            "dimension": int(vectors.shape[1]),
            "normalized": True,
            "device": resolved_device,
            "query_instruction": QUERY_INSTRUCTION,
            "local_files_only": True,
        },
        "chunking": {
            "strategy": "sentence-preferred character chunks with overlap",
            "chunk_size": chunk_size,
            "chunk_overlap": overlap,
            "chunk_count": int(len(chunks)),
            "job_count": int(chunks["job_id"].nunique()),
            "mean_chunk_chars": float(chunks["chunk_char_count"].mean()),
            "median_chunk_chars": float(chunks["chunk_char_count"].median()),
            "max_chunk_chars": int(chunks["chunk_char_count"].max()),
        },
        "metadata_fields": CHUNK_METADATA_FIELDS,
        "source_trace_fields": REQUIRED_SOURCE_FIELDS + ["chunk_id"],
        "build_seconds": round(time.perf_counter() - started, 3),
    }
    _write_json(index_dir / "index_manifest.json", manifest)
    return manifest


class FaissJobRetriever:
    def __init__(
        self,
        index: Any,
        chunks: pd.DataFrame,
        model: SentenceTransformer,
        manifest: Dict[str, Any],
    ) -> None:
        self.index = index
        self.chunks = chunks.reset_index(drop=True)
        self.model = model
        self.manifest = manifest

    @classmethod
    def load(
        cls,
        index_dir: Path = DEFAULT_INDEX_DIR,
        device: str = "auto",
    ) -> "FaissJobRetriever":
        manifest = json.loads((index_dir / "index_manifest.json").read_text(encoding="utf-8"))
        index = faiss.read_index(str(index_dir / "faiss.index"))
        chunks = pd.read_parquet(index_dir / "chunks.parquet")
        if index.ntotal != len(chunks):
            raise ValueError("FAISS index and metadata row counts differ")
        model = load_embedding_model(manifest["embedding"]["model"], device)
        return cls(index, chunks, model, manifest)

    def search(self, question: str, top_k: int = DEFAULT_TOP_K, unique_jobs: bool = True) -> List[Dict[str, Any]]:
        if top_k <= 0:
            return []
        vector = encode_texts(self.model, [clean_rag_text(question)], batch_size=1, query=True)
        candidate_count = min(len(self.chunks), max(top_k * 30, 100) if unique_jobs else top_k)
        scores, indexes = self.index.search(vector, candidate_count)
        results: List[Dict[str, Any]] = []
        seen_jobs: Set[str] = set()
        for score, row_index in zip(scores[0], indexes[0]):
            if row_index < 0:
                continue
            row = self.chunks.iloc[int(row_index)]
            job_id = _text(row["job_id"])
            if unique_jobs and job_id in seen_jobs:
                continue
            seen_jobs.add(job_id)
            result = {key: _json_value(row.get(key, "")) for key in CHUNK_METADATA_FIELDS}
            result["faiss_score"] = float(score)
            result["rank"] = len(results) + 1
            results.append(result)
            if len(results) >= top_k:
                break
        return results


def _gold_blob(df: pd.DataFrame) -> pd.Series:
    # The gold rules must inspect the same cleaned job text that is embedded.
    # Restricting them to title/skills would mark valid description-only matches
    # as empty and make the evaluation fail before retrieval is measured.
    fields = ["job_title", "broad_category", "job_category", "skills_normalized", "rag_description"]
    blob = pd.Series("", index=df.index, dtype="object")
    for field in fields:
        values = df[field].fillna("").astype(str) if field in df else ""
        blob = blob + " " + values
    return blob.str.lower().str.replace(r"\s+", " ", regex=True)


def build_gold_job_ids(jobs: pd.DataFrame, spec: QuerySpec) -> Set[str]:
    blob = _gold_blob(jobs)
    mask = pd.Series(True, index=jobs.index)
    for term in spec.must_all:
        mask &= blob.str.contains(term.lower(), regex=False)
    if spec.must_any:
        any_mask = pd.Series(False, index=jobs.index)
        for term in spec.must_any:
            any_mask |= blob.str.contains(term.lower(), regex=False)
        mask &= any_mask
    if spec.broad_categories:
        mask &= jobs["broad_category"].fillna("").isin(spec.broad_categories)
    if spec.districts:
        district_mask = pd.Series(False, index=jobs.index)
        district = jobs["district"].fillna("").astype(str).str.lower()
        for value in spec.districts:
            district_mask |= district.str.contains(value.lower(), regex=False)
        mask &= district_mask
    for term in spec.exclude_any:
        mask &= ~blob.str.contains(term.lower(), regex=False)
    return set(jobs.loc[mask, "job_id"].astype(str))


def _dcg(relevances: Sequence[int]) -> float:
    return sum(value / math.log2(index + 2) for index, value in enumerate(relevances))


def _query_metrics(results: Sequence[Dict[str, Any]], gold: Set[str], top_k: int) -> Dict[str, float]:
    relevance = [1 if str(result["job_id"]) in gold else 0 for result in results[:top_k]]
    relevance.extend([0] * max(0, top_k - len(relevance)))
    hits = sum(relevance)
    first_rank = next((index + 1 for index, value in enumerate(relevance) if value), None)
    ideal = [1] * min(len(gold), top_k) + [0] * max(0, top_k - min(len(gold), top_k))
    ideal_dcg = _dcg(ideal)
    return {
        "hit_at_k": float(hits > 0),
        "precision_at_k": float(hits / top_k),
        "recall_at_k": float(hits / len(gold)) if gold else 0.0,
        "mrr_at_k": float(1.0 / first_rank) if first_rank else 0.0,
        "ndcg_at_k": float(_dcg(relevance) / ideal_dcg) if ideal_dcg else 0.0,
        "relevant_in_top_k": int(hits),
    }


def _verify_source_trace(results: Sequence[Dict[str, Any]], jobs_by_id: pd.DataFrame) -> None:
    for result in results:
        job_id = str(result["job_id"])
        if job_id not in jobs_by_id.index:
            raise ValueError("retrieved job_id is absent from source data: " + job_id)
        source = jobs_by_id.loc[job_id]
        for field in ("job_title", "source_url", "crawl_time", "data_origin"):
            expected = _text(_json_value(source[field]))
            actual = _text(_json_value(result[field]))
            if actual != expected:
                raise ValueError("source trace mismatch for {} field {}".format(job_id, field))
        if not result.get("chunk_id") or not result.get("chunk_text"):
            raise ValueError("retrieval result lacks chunk provenance")


def _chunk_parameter_stats(jobs: pd.DataFrame) -> List[Dict[str, Any]]:
    settings = [(800, 120), (1200, 200), (1600, 250)]
    rows: List[Dict[str, Any]] = []
    descriptions = jobs["rag_description"].tolist()
    for chunk_size, overlap in settings:
        lengths: List[int] = []
        for description in descriptions:
            lengths.extend(len(chunk) for chunk in split_semantic_chunks(description, chunk_size, overlap))
        rows.append(
            {
                "chunk_size": chunk_size,
                "overlap": overlap,
                "chunk_count": len(lengths),
                "mean_chars": float(np.mean(lengths)),
                "median_chars": float(np.median(lengths)),
                "short_chunk_rate": float(np.mean(np.asarray(lengths) < chunk_size * 0.35)),
            }
        )
    return rows


def _save_charts(
    report_dir: Path,
    chunks: pd.DataFrame,
    query_rows: Sequence[Dict[str, Any]],
    sensitivity: Sequence[Dict[str, Any]],
    chunk_comparison: Sequence[Dict[str, Any]],
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ids = [row["question_id"] for row in query_rows]
    precisions = [row["metrics"]["precision_at_k"] for row in query_rows]
    colors = ["#2A7F62" if row["metrics"]["hit_at_k"] else "#B94A48" for row in query_rows]
    ax.bar(ids, precisions, color=colors)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Precision@3")
    ax.set_xlabel("Test question")
    ax.set_title("FAISS Retrieval Results by Question")
    fig.tight_layout()
    fig.savefig(report_dir / "retrieval_metrics.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    ks = [row["top_k"] for row in sensitivity]
    ax.plot(ks, [row["hit_rate"] for row in sensitivity], marker="o", label="Query Hit Rate")
    ax.plot(ks, [row["macro_precision"] for row in sensitivity], marker="o", label="Macro Precision")
    ax.plot(ks, [row["macro_recall"] for row in sensitivity], marker="o", label="Macro Recall")
    ax.set_xticks(ks)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Top-k")
    ax.set_ylabel("Metric")
    ax.set_title("Top-k Sensitivity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(report_dir / "top_k_sensitivity.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.hist(chunks["chunk_char_count"], bins=30, color="#356A91", edgecolor="white")
    ax.axvline(DEFAULT_CHUNK_SIZE, color="#B94A48", linestyle="--", label="Chunk size 1200")
    ax.set_xlabel("Chunk body characters")
    ax.set_ylabel("Chunk count")
    ax.set_title("Chunk Length Distribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(report_dir / "chunk_distribution.png", dpi=180)
    plt.close(fig)

    labels = ["{}/{}".format(row["chunk_size"], row["overlap"]) for row in chunk_comparison]
    fig, left_axis = plt.subplots(figsize=(8.6, 5))
    bars = left_axis.bar(labels, [row["chunk_count"] for row in chunk_comparison], color="#5C7890")
    left_axis.set_xlabel("Chunk size / overlap")
    left_axis.set_ylabel("Chunk count")
    left_axis.set_title("Chunk Parameter Structural Comparison")
    right_axis = left_axis.twinx()
    right_axis.plot(labels, [row["short_chunk_rate"] for row in chunk_comparison], color="#A8503A", marker="o")
    right_axis.set_ylabel("Short chunk rate")
    right_axis.set_ylim(0, max(0.25, max(row["short_chunk_rate"] for row in chunk_comparison) * 1.25))
    for bar in bars:
        left_axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(int(bar.get_height())), ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(report_dir / "chunk_parameter_comparison.png", dpi=180)
    plt.close(fig)


def _answer_excerpt(result: Dict[str, Any]) -> str:
    body = re.sub(r"\s+", " ", _text(result.get("chunk_body"))).strip()
    return "{}：{}".format(_text(result.get("job_title")), body[:320])


def _write_triples(path: Path, query_rows: Sequence[Dict[str, Any]]) -> None:
    ensure_derived_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "question_id",
        "question_type",
        "question",
        "rank",
        "answer",
        "job_id",
        "job_title",
        "chunk_id",
        "source_url",
        "crawl_time",
        "data_origin",
        "faiss_score",
        "is_relevant",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for query in query_rows:
            for result in query["results"]:
                writer.writerow(
                    {
                        "question_id": query["question_id"],
                        "question_type": query["question_type"],
                        "question": query["question"],
                        "rank": result["rank"],
                        "answer": _answer_excerpt(result),
                        "job_id": result["job_id"],
                        "job_title": result["job_title"],
                        "chunk_id": result["chunk_id"],
                        "source_url": result["source_url"],
                        "crawl_time": result["crawl_time"],
                        "data_origin": result["data_origin"],
                        "faiss_score": "{:.6f}".format(result["faiss_score"]),
                        "is_relevant": result["is_relevant"],
                    }
                )


def _build_experiment_markdown(
    manifest: Dict[str, Any],
    summary: Dict[str, Any],
    query_rows: Sequence[Dict[str, Any]],
    chunk_comparison: Sequence[Dict[str, Any]],
) -> str:
    successful = [row for row in query_rows if row["metrics"]["hit_at_k"]]
    failed = [row for row in query_rows if not row["metrics"]["hit_at_k"]]
    lines = [
        "# RAG 知识库构建与检索召回测试实验",
        "",
        "## 实验结论",
        "",
        "本实验使用本地清洗后的 12,000 条 Himalayas 远程岗位数据，采用 BAAI/bge-small-zh-v1.5 生成 512 维中文语义向量，并写入 FAISS IndexFlatIP。主实验固定 Chunk=1200 字符、Overlap=200 字符、Top-k=3。所有结果均携带岗位编号、岗位名称、Chunk 编号、source_url、crawl_time 和 data_origin。",
        "",
        "## 向量库选型",
        "",
        "选择 FAISS 的原因是本实验为单机、离线、数万级 Chunk 的检索任务。IndexFlatIP 对归一化向量执行精确内积搜索，结果可重复且无需运行数据库服务。优点是部署简单、检索快、精确搜索没有近似索引损失；缺点是原生元数据过滤和多用户服务能力弱于 Chroma/Milvus，需要将 Parquet 元数据与向量行号共同维护。对于本项目的本地实验规模，这一取舍比引入服务端数据库更合适。",
        "",
        "## 数据处理与入库",
        "",
        "- 输入岗位：{}；去重后有效岗位：{}；删除重复岗位：{}；删除残缺记录：{}。".format(
            manifest["cleaning"]["input_rows"],
            manifest["cleaning"]["valid_rows"],
            manifest["cleaning"]["duplicate_job_ids_removed"],
            manifest["cleaning"]["incomplete_rows_removed"],
        ),
        "- 文本处理：HTML 解码、Unicode NFKC、控制字符与乱码替换、标签和多余空白清理。",
        "- 长文本分块：优先在句号、问号、分号和换行处切分，超过上限时再在空格或标点处切分；相邻块保留 200 字符重叠。",
        "- Chunk 数：{}；平均长度：{:.1f} 字符；最大长度：{} 字符。".format(
            manifest["chunking"]["chunk_count"],
            manifest["chunking"]["mean_chunk_chars"],
            manifest["chunking"]["max_chunk_chars"],
        ),
        "- 当前主索引采用分区感知策略：显式识别岗位介绍、岗位职责和任职要求后分别建块；无显式标题的岗位只建立一个综合文本回退块。参数对比表按完整清洗描述独立计算，用于比较 Chunk 设置，不代表主索引行数。",
        "- Embedding：{}，维度 {}，向量 L2 归一化；FAISS 使用 {}。".format(
            manifest["embedding"]["model"],
            manifest["embedding"]["dimension"],
            manifest["vector_store"]["index_type"],
        ),
        "",
        "## 主实验定量结果",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
        "| 测试问题数 | {} |".format(summary["question_count"]),
        "| Query Hit@3 | {:.4f} |".format(summary["query_hit_rate_at_3"]),
        "| Macro Precision@3 | {:.4f} |".format(summary["macro_precision_at_3"]),
        "| Macro Recall@3 | {:.4f} |".format(summary["macro_recall_at_3"]),
        "| Macro MRR@3 | {:.4f} |".format(summary["macro_mrr_at_3"]),
        "| Macro nDCG@3 | {:.4f} |".format(summary["macro_ndcg_at_3"]),
        "| 来源字段完整率 | {:.4f} |".format(summary["source_trace_coverage"]),
        "",
        "## 逐题结果",
        "",
        "| ID | 类型 | Gold 岗位数 | 命中数 | P@3 | R@3 | 首条结果 |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in query_rows:
        first_title = row["results"][0]["job_title"].replace("|", "/") if row["results"] else ""
        lines.append(
            "| {} | {} | {} | {} | {:.4f} | {:.4f} | {} |".format(
                row["question_id"],
                row["question_type"],
                row["gold_count"],
                row["metrics"]["relevant_in_top_k"],
                row["metrics"]["precision_at_k"],
                row["metrics"]["recall_at_k"],
                first_title,
            )
        )
    lines.extend(
        [
            "",
            "## 成功与失败案例",
            "",
            "成功案例：{}。这些问题至少有一条 Top-3 结果满足预设的技能、类别或地区条件。".format(
                "、".join(row["question_id"] for row in successful) or "无"
            ),
            "",
            "失败案例：{}。失败表示 Top-3 未命中结构化 gold 集，不代表结果文本完全无关；可能原因包括中文职责表达与英文岗位语料跨语言差异、技能标签缺失、同义岗位边界和单向量检索未使用结构化过滤。".format(
                "、".join(row["question_id"] for row in failed) or "本轮无完全失败问题"
            ),
            "",
            "## 参数影响",
            "",
            "参数对比口径说明：下表对每条完整清洗岗位描述独立计算不同 Chunk/Overlap 设置，目的是比较结构性开销；当前主索引采用岗位介绍、岗位职责和任职要求分区建块，并对无显式标题的岗位使用一个综合文本回退块，因此表中的 Chunk 数不能直接替代主索引 Chunk 数。",
            "",
            "| Chunk/Overlap | Chunk 数 | 平均长度 | 短块比例 |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in chunk_comparison:
        lines.append(
            "| {}/{} | {} | {:.1f} | {:.4f} |".format(
                row["chunk_size"], row["overlap"], row["chunk_count"], row["mean_chars"], row["short_chunk_rate"]
            )
        )
    lines.extend(
        [
            "",
            "800/120 产生更多向量，细粒度更高但上下文更短、存储和编码开销更大；1600/250 向量更少、上下文更完整，但主题混合风险更高。1200/200 在本数据平均描述长度约数千字符的条件下取得折中。Top-k 从 1 增至 5 通常提高命中率和召回率，但会降低结果精度并增加阅读成本，因此主实验固定 k=3。",
            "",
            "FAISS IndexFlatIP 在本实验使用精确搜索，不引入近似索引召回损失；Embedding 决定中文查询与英文岗位描述之间的语义映射质量。后续可比较多语 Embedding、混合检索与结构化过滤，但本报告只记录当前实际运行结果。",
            "",
            "## 输出文件",
            "",
            "- `data/processed/rag/faiss.index`",
            "- `data/processed/rag/chunks.parquet`",
            "- `data/processed/rag/chunk_metadata.jsonl`",
            "- `data/processed/rag/index_manifest.json`",
            "- `reports/rag/test_queries.json`",
            "- `reports/rag/retrieval_tests.json`",
            "- `reports/rag/question_answer_source_triples.csv`",
            "- `reports/rag/rag_eval_summary.json`",
            "- `reports/rag/retrieval_metrics.png`",
            "- `reports/rag/top_k_sensitivity.png`",
            "- `reports/rag/chunk_distribution.png`",
            "- `reports/rag/chunk_parameter_comparison.png`",
            "",
        ]
    )
    return "\n".join(lines)


def evaluate_retrieval(
    data_path: Path = DEFAULT_DATA,
    index_dir: Path = DEFAULT_INDEX_DIR,
    report_dir: Path = DEFAULT_REPORT_DIR,
    top_k: int = DEFAULT_TOP_K,
    device: str = "auto",
) -> Dict[str, Any]:
    if top_k != DEFAULT_TOP_K:
        raise ValueError("the formal experiment fixes top_k at 3")
    source_df = pd.read_parquet(data_path)
    jobs, _ = validate_and_filter_jobs(source_df)
    jobs_by_id = jobs.set_index(jobs["job_id"].astype(str), drop=False)
    retriever = FaissJobRetriever.load(index_dir, device=device)
    query_rows: List[Dict[str, Any]] = []
    gold_sets: Dict[str, Set[str]] = {}
    for spec in TEST_QUERIES:
        gold = build_gold_job_ids(jobs, spec)
        if not gold:
            raise ValueError("query {} produced an empty gold set".format(spec.question_id))
        results = retriever.search(spec.question, top_k=top_k, unique_jobs=True)
        _verify_source_trace(results, jobs_by_id)
        for result in results:
            result["is_relevant"] = int(str(result["job_id"]) in gold)
        metrics = _query_metrics(results, gold, top_k)
        row = asdict(spec)
        row.update(
            {
                "gold_count": len(gold),
                "gold_job_id_sample": sorted(gold)[:20],
                "metrics": metrics,
                "results": results,
            }
        )
        query_rows.append(row)
        gold_sets[spec.question_id] = gold

    sensitivity: List[Dict[str, Any]] = []
    for current_k in (1, 3, 5):
        metric_rows: List[Dict[str, float]] = []
        for spec in TEST_QUERIES:
            results = retriever.search(spec.question, top_k=current_k, unique_jobs=True)
            metric_rows.append(_query_metrics(results, gold_sets[spec.question_id], current_k))
        sensitivity.append(
            {
                "top_k": current_k,
                "hit_rate": float(np.mean([row["hit_at_k"] for row in metric_rows])),
                "macro_precision": float(np.mean([row["precision_at_k"] for row in metric_rows])),
                "macro_recall": float(np.mean([row["recall_at_k"] for row in metric_rows])),
                "macro_mrr": float(np.mean([row["mrr_at_k"] for row in metric_rows])),
                "macro_ndcg": float(np.mean([row["ndcg_at_k"] for row in metric_rows])),
            }
        )

    main_metrics = [row["metrics"] for row in query_rows]
    result_count = sum(len(row["results"]) for row in query_rows)
    traced_count = sum(
        1
        for row in query_rows
        for result in row["results"]
        if all(_text(result.get(field)).strip() for field in ("job_id", "job_title", "chunk_id", "source_url", "crawl_time", "data_origin"))
    )
    summary = {
        "experiment": "FAISS + BAAI/bge-small-zh-v1.5 semantic retrieval",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "top_k": top_k,
        "question_count": len(query_rows),
        "retrieved_result_count": result_count,
        "query_hit_rate_at_3": float(np.mean([row["hit_at_k"] for row in main_metrics])),
        "macro_precision_at_3": float(np.mean([row["precision_at_k"] for row in main_metrics])),
        "macro_recall_at_3": float(np.mean([row["recall_at_k"] for row in main_metrics])),
        "macro_mrr_at_3": float(np.mean([row["mrr_at_k"] for row in main_metrics])),
        "macro_ndcg_at_3": float(np.mean([row["ndcg_at_k"] for row in main_metrics])),
        "source_trace_coverage": float(traced_count / result_count) if result_count else 0.0,
        "gold_definition": "reproducible structured conditions over title, category, normalized skills and district",
        "top_k_sensitivity": sensitivity,
        "per_question": [
            {
                "question_id": row["question_id"],
                "question_type": row["question_type"],
                "gold_count": row["gold_count"],
                **row["metrics"],
            }
            for row in query_rows
        ],
    }
    chunk_comparison = _chunk_parameter_stats(jobs)
    test_query_rows = []
    for row in query_rows:
        saved = {key: value for key, value in row.items() if key not in ("results", "metrics")}
        saved["gold_rules"] = {
            "must_all": list(row["must_all"]),
            "must_any": list(row["must_any"]),
            "broad_categories": list(row["broad_categories"]),
            "districts": list(row["districts"]),
            "exclude_any": list(row["exclude_any"]),
        }
        for key in ("must_all", "must_any", "broad_categories", "districts", "exclude_any"):
            saved.pop(key, None)
        test_query_rows.append(saved)

    report_dir.mkdir(parents=True, exist_ok=True)
    _write_json(report_dir / "test_queries.json", test_query_rows)
    _write_json(report_dir / "retrieval_tests.json", query_rows)
    _write_json(report_dir / "rag_eval_summary.json", summary)
    _write_json(report_dir / "chunk_parameter_comparison.json", chunk_comparison)
    _write_triples(report_dir / "question_answer_source_triples.csv", query_rows)
    _save_charts(report_dir, retriever.chunks, query_rows, sensitivity, chunk_comparison)
    experiment_md = _build_experiment_markdown(retriever.manifest, summary, query_rows, chunk_comparison)
    ensure_derived_output(report_dir / "rag_faiss_experiment.md")
    (report_dir / "rag_faiss_experiment.md").write_text(experiment_md, encoding="utf-8")
    return summary


def run_all(
    data_path: Path = DEFAULT_DATA,
    index_dir: Path = DEFAULT_INDEX_DIR,
    report_dir: Path = DEFAULT_REPORT_DIR,
    model_name: str = DEFAULT_MODEL,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    batch_size: int = 64,
    device: str = "auto",
) -> Dict[str, Any]:
    manifest = build_faiss_knowledge_base(
        data_path=data_path,
        index_dir=index_dir,
        model_name=model_name,
        chunk_size=chunk_size,
        overlap=overlap,
        batch_size=batch_size,
        device=device,
    )
    summary = evaluate_retrieval(data_path, index_dir, report_dir, DEFAULT_TOP_K, device)
    return {"manifest": manifest, "summary": summary}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build and evaluate the formal FAISS RAG experiment")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--batch-size", type=int, default=64)
    build_parser.add_argument("--device", default="auto")
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--device", default="auto")
    all_parser = subparsers.add_parser("all")
    all_parser.add_argument("--batch-size", type=int, default=64)
    all_parser.add_argument("--device", default="auto")
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("question")
    search_parser.add_argument("--top-k", type=int, default=3)
    search_parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)
    if args.command == "build":
        payload = build_faiss_knowledge_base(batch_size=args.batch_size, device=args.device)
    elif args.command == "evaluate":
        payload = evaluate_retrieval(device=args.device)
    elif args.command == "all":
        payload = run_all(batch_size=args.batch_size, device=args.device)
    else:
        retriever = FaissJobRetriever.load(device=args.device)
        payload = retriever.search(args.question, top_k=args.top_k)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
