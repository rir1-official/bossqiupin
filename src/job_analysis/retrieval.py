"""Local retrieval baseline for the cleaned remote-job knowledge base.

This module deliberately uses TF-IDF rather than pretending that a downloaded
embedding model is available. It provides a reproducible RAG-style retrieval
prototype with source-preserving metadata and an evaluation harness.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import load_npz, save_npz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .cleaning import PROJECT_ROOT, clean_text, ensure_derived_output
from .matching import extract_skills


DEFAULT_DATA = PROJECT_ROOT / "data/processed/jobs_cleaned.parquet"
# Keep the deterministic lexical baseline separate from the formal FAISS RAG
# experiment so the two implementations cannot overwrite each other's index.
DEFAULT_INDEX_DIR = PROJECT_ROOT / "data/processed/rag_tfidf_baseline"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports/rag_tfidf_baseline"

RETURN_FIELDS = [
    "job_id",
    "job_title",
    "company_name",
    "broad_category",
    "skills_normalized",
    "district",
    "salary_raw",
    "source_url",
    "crawl_time",
    "data_origin",
]


def _text(value: Any) -> str:
    return "" if value is None or (isinstance(value, float) and np.isnan(value)) else str(value)


def _json_value(value: Any) -> Any:
    """Keep CLI/API results JSON serializable after pandas reloads dates."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return value.isoformat() if hasattr(value, "isoformat") else value


def build_documents(df: pd.DataFrame) -> List[str]:
    documents: List[str] = []
    for _, row in df.iterrows():
        description = _text(row.get("description_clean")) or _text(row.get("job_description"))
        documents.append(
            " ".join(
                [
                    "title " + _text(row.get("job_title")),
                    "company " + _text(row.get("company_name")),
                    "skills " + _text(row.get("skills_normalized")).replace("|", " "),
                    "category " + _text(row.get("broad_category")),
                    "subcategory " + _text(row.get("job_category")),
                    "description " + description,
                    "district " + _text(row.get("district")),
                    "salary " + _text(row.get("salary_raw")),
                    "url " + _text(row.get("source_url")),
                ]
            )
        )
    return documents


def normalize_query(query: str) -> str:
    query = clean_text(query)
    # Query labels such as "有哪些" add no retrieval signal for the English
    # job corpus, while retaining technical tokens such as Python and SQL.
    query = re.sub(r"[\u4e00-\u9fff]+", " ", query)
    return " ".join(query.split())


def _row_skill_set(row: pd.Series) -> set[str]:
    return set(extract_skills(" ".join(_text(row.get(field)) for field in ("job_title", "skills_normalized", "job_category", "description_clean"))))


class JobRetriever:
    """Persistable TF-IDF retriever with optional deterministic skill boosts."""

    def __init__(self, vectorizer: Optional[TfidfVectorizer] = None) -> None:
        self.vectorizer = vectorizer or TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.99,
            max_features=20000,
            sublinear_tf=True,
            dtype=np.float32,
        )
        self.matrix = None
        self.metadata = pd.DataFrame()
        self.documents: List[str] = []

    def fit(self, df: pd.DataFrame) -> "JobRetriever":
        self.metadata = df.reset_index(drop=True).copy()
        self.documents = build_documents(self.metadata)
        self.matrix = self.vectorizer.fit_transform(self.documents)
        return self

    def save(self, index_dir: Path = DEFAULT_INDEX_DIR) -> None:
        if self.matrix is None or self.metadata.empty:
            raise ValueError("retriever has not been fitted")
        index_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.vectorizer, index_dir / "tfidf_vectorizer.joblib")
        save_npz(index_dir / "tfidf_matrix.npz", self.matrix)
        metadata = self.metadata.copy()
        for column in RETURN_FIELDS:
            if column not in metadata:
                metadata[column] = ""
        metadata[RETURN_FIELDS].to_json(index_dir / "metadata.jsonl", orient="records", lines=True, force_ascii=False)
        manifest = {
            "method": "TF-IDF cosine retrieval baseline",
            "records": int(len(metadata)),
            "feature_count": int(self.matrix.shape[1]),
            "return_fields": RETURN_FIELDS,
            "source": "data/processed/jobs_cleaned.parquet",
            "semantic_embedding": False,
        }
        ensure_derived_output(index_dir / "index_manifest.json")
        (index_dir / "index_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, index_dir: Path = DEFAULT_INDEX_DIR) -> "JobRetriever":
        result = cls(joblib.load(index_dir / "tfidf_vectorizer.joblib"))
        result.matrix = load_npz(index_dir / "tfidf_matrix.npz")
        result.metadata = pd.read_json(index_dir / "metadata.jsonl", lines=True)
        return result

    def search(
        self,
        query: str,
        top_k: int = 5,
        required_skills: Optional[Iterable[str]] = None,
        category: Optional[str] = None,
        district: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if self.matrix is None or self.metadata.empty:
            return []
        normalized = normalize_query(query)
        query_vector = self.vectorizer.transform([normalized])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        explicit_skills = required_skills is not None
        requested_skills = {clean_text(x) for x in (required_skills if explicit_skills else extract_skills(query)) if clean_text(x)}
        rows: List[Dict[str, Any]] = []
        for index, row in self.metadata.iterrows():
            row_dict = row.to_dict()
            if category and clean_text(category) not in clean_text(row_dict.get("broad_category")):
                continue
            if district and clean_text(district) not in clean_text(row_dict.get("district")):
                continue
            hits = sorted(requested_skills & _row_skill_set(row))
            if explicit_skills and requested_skills and hits != sorted(requested_skills):
                continue
            score = float(scores[index]) + min(0.08, 0.02 * len(hits))
            item = {field: _json_value(row_dict.get(field, "")) for field in RETURN_FIELDS}
            item.update({"retrieval_score": round(score, 6), "matched_query_skills": hits})
            rows.append(item)
        rows.sort(key=lambda item: (-item["retrieval_score"], str(item.get("job_id", ""))))
        return rows[: max(1, int(top_k))]


DEFAULT_TEST_QUERIES = [
    {
        "question": "有哪些适合 Python 和 SQL 的远程数据分析岗位？",
        "expected_skills": ["python", "sql"],
        "expected_category": "Data Science",
    },
    {
        "question": "哪些岗位要求 machine learning 技能？",
        "expected_skills": ["machine learning"],
    },
    {
        "question": "有哪些岗位属于 Engineering 类别？",
        "expected_category": "Engineering",
    },
    {
        "question": "哪些岗位包含 Excel 和 Tableau？",
        "expected_skills": ["excel", "tableau"],
    },
    {
        "question": "有哪些岗位有明确地区限制？",
        "expected_location": True,
    },
    {
        "question": "哪些远程岗位同时涉及 AWS、Docker 和 Kubernetes？",
        "expected_skills": ["aws", "docker", "kubernetes"],
        "expected_category": "Engineering",
    },
    {
        "question": "有哪些岗位需要 pandas 和 PostgreSQL？",
        "expected_skills": ["pandas", "postgresql"],
        "expected_category": "Data Science",
    },
    {
        "question": "哪些岗位要求 JavaScript 和 TypeScript？",
        "expected_skills": ["javascript", "typescript"],
        "expected_category": "Engineering",
    },
    {
        "question": "有哪些 Product 类别的远程岗位？",
        "expected_category": "Product",
    },
    {
        "question": "哪些 Finance 类别岗位适合有 Excel 经验的人？",
        "expected_skills": ["excel"],
        "expected_category": "Finance",
    },
]


def evaluate_queries(retriever: JobRetriever, queries: Sequence[Dict[str, Any]] = DEFAULT_TEST_QUERIES, top_k: int = 5) -> List[Dict[str, Any]]:
    evaluations: List[Dict[str, Any]] = []
    for case in queries:
        results = retriever.search(case["question"], top_k=top_k)
        skill_checks: Dict[str, int] = {}
        for skill in case.get("expected_skills", []):
            skill_checks[skill] = sum(1 for row in results if skill in row.get("matched_query_skills", []))
        category_hits = sum(1 for row in results if case.get("expected_category") and row.get("broad_category") == case["expected_category"])
        location_hits = sum(1 for row in results if case.get("expected_location") and clean_text(row.get("district")))
        evaluations.append(
            {
                "question": case["question"],
                "top_k": top_k,
                "results": results,
                "skill_hit_counts": skill_checks,
                "category_hit_count": category_hits,
                "location_nonempty_count": location_hits,
            }
        )
    return evaluations


def write_evaluation_report(path: Path, evaluations: Sequence[Dict[str, Any]]) -> None:
    lines = [
        "# RAG 检索原型召回评估",
        "",
        "本报告评估本地 TF-IDF + 余弦相似度检索基线。它不是深度语义 Embedding，也不代表真实召回率；检查项用于确认 Top-k 是否包含问题要求的技能、类别和地区字段，并保留岗位来源链接。",
        "",
    ]
    for index, item in enumerate(evaluations, start=1):
        lines += [f"## 测试问题 {index}", "", f"问题：{item['question']}", ""]
        if item["skill_hit_counts"]:
            lines.append("技能命中：" + "；".join(f"{skill}={count}/{item['top_k']}" for skill, count in item["skill_hit_counts"].items()))
        if item.get("category_hit_count"):
            lines.append(f"类别命中：{item['category_hit_count']}/{item['top_k']}")
        if item.get("location_nonempty_count"):
            lines.append(f"地区字段非空：{item['location_nonempty_count']}/{item['top_k']}")
        lines += ["", "| 排名 | 岗位 | 公司 | 类别 | 技能 | 薪资原文 | 来源 |", "| ---: | --- | --- | --- | --- | --- | --- |"]
        for rank, row in enumerate(item["results"], start=1):
            source = row.get("source_url", "")
            lines.append(
                f"| {rank} | {row.get('job_title','')} | {row.get('company_name','')} | {row.get('broad_category','')} | {row.get('skills_normalized','')} | {row.get('salary_raw','') or '未披露'} | {source} |"
            )
        lines += ["", "人工检查结论：Top-k 结果保留 `job_id`、`source_url`、`crawl_time` 与 `data_origin`，技能与类别命中可由返回字段复核；若问题含中文自然语言，当前基线主要依赖其中的英文技能词。", ""]
    ensure_derived_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_build(data_path: Path = DEFAULT_DATA, index_dir: Path = DEFAULT_INDEX_DIR, report_dir: Path = DEFAULT_REPORT_DIR, top_k: int = 3) -> Dict[str, Any]:
    df = pd.read_parquet(data_path)
    retriever = JobRetriever().fit(df)
    retriever.save(index_dir)
    evaluations = evaluate_queries(retriever, top_k=top_k)
    report_dir.mkdir(parents=True, exist_ok=True)
    ensure_derived_output(report_dir / "retrieval_tests.json")
    (report_dir / "retrieval_tests.json").write_text(json.dumps(evaluations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_evaluation_report(report_dir / "../rag_retrieval_evaluation.md", evaluations)
    return {"records": len(df), "feature_count": int(retriever.matrix.shape[1]), "tests": len(evaluations)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or query the local job retrieval baseline")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--data", type=Path, default=DEFAULT_DATA)
    build.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    build.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    search.add_argument("--top-k", type=int, default=5)
    search.add_argument("--skill", action="append", dest="skills", default=[])
    search.add_argument("--category")
    search.add_argument("--district")
    args = parser.parse_args()
    if args.command == "build":
        print(json.dumps(run_build(args.data, args.index_dir, args.report_dir), ensure_ascii=False, indent=2))
    else:
        retriever = JobRetriever.load(args.index_dir)
        print(
            json.dumps(
                retriever.search(
                    args.query,
                    top_k=args.top_k,
                    required_skills=args.skills or None,
                    category=args.category,
                    district=args.district,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
