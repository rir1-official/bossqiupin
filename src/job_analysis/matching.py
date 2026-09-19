"""Resume-to-job matching with TF-IDF cosine similarity and rule-based explanations."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .cleaning import clean_text, tokenize_text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = PROJECT_ROOT / "data/processed/jobs_cleaned.parquet"


@dataclass
class MatchingIndex:
    """Reusable TF-IDF representation for the immutable cleaned job table."""

    vectorizer: TfidfVectorizer
    matrix: Any
    records: List[Dict[str, Any]]
    skill_sets: List[Set[str]]


def build_matching_index(jobs: pd.DataFrame) -> MatchingIndex:
    """Fit the job-side vocabulary once for repeated API matching requests.

    The cleaned Parquet is treated as an immutable dataset during an API
    process. Fitting on job documents only means each request transforms one
    resume vector instead of rebuilding 12,000 job vectors.
    """
    records = jobs.to_dict(orient="records")
    job_texts = [_job_vector_text(row) for row in records]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    matrix = vectorizer.fit_transform(job_texts)
    skill_sets = [_job_skill_set(row) for row in records]
    return MatchingIndex(vectorizer=vectorizer, matrix=matrix, records=records, skill_sets=skill_sets)

SKILL_ALIASES = {
    "python": "python",
    "sql": "sql",
    "r programming": "r",
    " r ": "r",
    "java": "java",
    "javascript": "javascript",
    "typescript": "typescript",
    "golang": "go",
    " go ": "go",
    "aws": "aws",
    "amazon web services": "aws",
    "azure": "azure",
    "gcp": "gcp",
    "google cloud": "gcp",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "terraform": "terraform",
    "linux": "linux",
    "git": "git",
    "rest api": "rest api",
    "restful": "rest api",
    "grpc": "grpc",
    "graphql": "graphql",
    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "machine learning": "machine learning",
    "deep learning": "deep learning",
    "nlp": "nlp",
    "natural language processing": "nlp",
    "tableau": "tableau",
    "power bi": "power bi",
    "excel": "excel",
    "pandas": "pandas",
    "numpy": "numpy",
    "spark": "spark",
    "hadoop": "hadoop",
    "airflow": "airflow",
    "dbt": "dbt",
    "snowflake": "snowflake",
    "mongodb": "mongodb",
    "postgresql": "postgresql",
    "mysql": "mysql",
    "redis": "redis",
    "salesforce": "salesforce",
    "agile": "agile",
    "scrum": "scrum",
    "project management": "project management",
}

CATEGORY_TERMS = {
    "Data Science": ("data", "analytics", "machine learning", "data scientist", "data analyst"),
    "Engineering": ("engineer", "developer", "software", "backend", "frontend", "devops", "infrastructure"),
    "Sales": ("sales", "account executive", "business development"),
    "Customer Service": ("customer service", "customer support", "customer success"),
    "Marketing": ("marketing", "growth", "seo", "social media"),
    "Operations": ("operations", "project management", "program management"),
    "Product": ("product manager", "product management"),
    "Finance": ("finance", "accounting", "financial"),
    "Human Resources": ("human resources", "recruit", "talent", "people operations"),
    "Healthcare": ("healthcare", "medical", "clinical"),
    "Design": ("design", "ux", "ui"),
    "Legal": ("legal", "attorney", "lawyer", "counsel"),
}


def extract_pdf_text(path: Path) -> str:
    """Extract selectable text from a PDF; OCR is intentionally outside this version."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def normalize_resume_text(text: str) -> str:
    return " ".join(tokenize_text(clean_text(text)))


def _contains_term(text: str, term: str) -> bool:
    term = term.strip().lower()
    if len(term) <= 2:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text))
    return term in text


def extract_skills(text: str) -> Set[str]:
    lowered = f" {clean_text(text)} "
    found: Set[str] = set()
    for alias, canonical in SKILL_ALIASES.items():
        if _contains_term(lowered, alias):
            found.add(canonical)
    return found


def extract_years(text: str) -> Optional[float]:
    lowered = clean_text(text)
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?|年)", lowered)
    if not matches:
        return None
    return max(float(value) for value in matches)


def infer_category(text: str) -> Optional[str]:
    lowered = clean_text(text)
    scores = {
        category: sum(1 for term in terms if term in lowered)
        for category, terms in CATEGORY_TERMS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else None


def _job_skill_set(row: Dict[str, Any]) -> Set[str]:
    source = " ".join(
        str(row.get(field) or "")
        for field in ("job_title", "skills_normalized", "job_category", "description_clean")
    )
    return extract_skills(source)


def _job_vector_text(row: Dict[str, Any]) -> str:
    """Reuse persisted tokens so ranking 12k jobs does not re-run jieba."""
    fields = [
        str(row.get("job_title") or ""),
        str(row.get("skills_normalized") or ""),
        str(row.get("job_category") or ""),
        str(row.get("description_tokens") or row.get("description_clean") or ""),
    ]
    return normalize_resume_text(" ".join(fields)) if not row.get("description_tokens") else " ".join(
        token for token in clean_text(" ".join(fields)).split() if token
    )


def _category_score(resume_category: Optional[str], row: Dict[str, Any]) -> float:
    job_category = str(row.get("broad_category") or "")
    if not resume_category or not job_category:
        return 50.0
    if resume_category == job_category:
        return 100.0
    return 0.0


def _experience_score(resume_years: Optional[float], row: Dict[str, Any]) -> float:
    if resume_years is None:
        return 50.0
    minimum = row.get("experience_year_min")
    maximum = row.get("experience_year_max")
    if pd.isna(minimum) or pd.isna(maximum):
        return 50.0
    minimum, maximum = float(minimum), float(maximum)
    if minimum <= resume_years <= maximum:
        return 100.0
    gap = minimum - resume_years if resume_years < minimum else resume_years - maximum
    return max(0.0, 100.0 - gap * 20.0)


def _location_score(preferred_locations: Optional[Iterable[str]], row: Dict[str, Any]) -> float:
    district = clean_text(row.get("district") or "")
    if not district or district == "remote":
        return 100.0
    locations = {clean_text(value) for value in (preferred_locations or []) if clean_text(value)}
    if not locations:
        return 50.0
    return 100.0 if any(location in district for location in locations) else 0.0


def match_jobs(
    resume_text: str,
    jobs: pd.DataFrame,
    top_k: int = 10,
    resume_category: Optional[str] = None,
    resume_years: Optional[float] = None,
    preferred_locations: Optional[Iterable[str]] = None,
    matching_index: Optional[MatchingIndex] = None,
) -> List[Dict[str, Any]]:
    """Rank jobs using the documented weighted score and return explainable rows."""
    if not resume_text or jobs.empty:
        return []
    resume_clean = normalize_resume_text(resume_text)
    index = matching_index or build_matching_index(jobs)
    resume_vector = index.vectorizer.transform([resume_clean])
    similarities = cosine_similarity(resume_vector, index.matrix).ravel()
    resume_skills = extract_skills(resume_text)
    records = index.records if matching_index is not None else jobs.to_dict(orient="records")
    skill_sets = index.skill_sets if matching_index is not None else [_job_skill_set(row) for row in records]
    results: List[Dict[str, Any]] = []
    for position, row in enumerate(records):
        job_skills = skill_sets[position]
        matched = sorted(resume_skills & job_skills)
        missing = sorted(job_skills - resume_skills)
        overlap = len(matched) / len(job_skills) if job_skills else 0.0
        skill_score = 100.0 * (0.7 * float(similarities[position]) + 0.3 * overlap)
        category_score = _category_score(resume_category or infer_category(resume_text), row)
        experience_score = _experience_score(resume_years if resume_years is not None else extract_years(resume_text), row)
        location_score = _location_score(preferred_locations, row)
        total = 0.55 * skill_score + 0.20 * category_score + 0.15 * experience_score + 0.10 * location_score
        results.append(
            {
                "job_id": row.get("job_id", ""),
                "job_title": row.get("job_title", ""),
                "company_name": row.get("company_name", ""),
                "district": row.get("district", ""),
                "source_url": row.get("source_url", ""),
                "crawl_time": row.get("crawl_time", ""),
                "data_origin": row.get("data_origin", ""),
                "match_score": round(total, 2),
                "skill_score": round(skill_score, 2),
                "category_score": round(category_score, 2),
                "experience_score": round(experience_score, 2),
                "location_score": round(location_score, 2),
                "cosine_similarity": round(float(similarities[position]), 4),
                "matched_skills": matched,
                "missing_skills": missing,
                "salary_reference": row.get("salary_raw", "") or "未披露",
                "quality_level": row.get("quality_level", ""),
            }
        )
    results.sort(key=lambda item: (-item["match_score"], item["job_id"]))
    for item in results:
        item["explanation"] = build_explanation(item)
    return results[:top_k]


def build_explanation(result: Dict[str, Any]) -> str:
    matched = "、".join(result["matched_skills"][:5]) or "未识别到明确技能交集"
    missing = "、".join(result["missing_skills"][:5]) or "暂无主要技能缺口"
    return (
        f"综合匹配分 {result['match_score']:.2f}。技能相似度分项 {result['skill_score']:.2f}，"
        f"命中技能：{matched}；主要缺失技能：{missing}。"
        f"岗位类别分项 {result['category_score']:.2f}，经验分项 {result['experience_score']:.2f}，"
        f"地点分项 {result['location_score']:.2f}。薪资仅作参考：{result['salary_reference']}。"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Match a resume against cleaned job data")
    parser.add_argument("resume")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    resume_path = Path(args.resume)
    resume_text = extract_pdf_text(resume_path) if resume_path.suffix.lower() == ".pdf" else resume_path.read_text(encoding="utf-8")
    jobs = pd.read_parquet(args.data)
    output = match_jobs(resume_text, jobs, top_k=args.top_k)
    payload = {"input_type": "pdf" if resume_path.suffix.lower() == ".pdf" else "text", "results": output}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
