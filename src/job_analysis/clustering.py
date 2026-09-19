"""K-Means clustering for cleaned remote-job records.

The implementation keeps the feature space interpretable: title, skills,
category and description are combined into a weighted TF-IDF representation.
It writes all derived artifacts outside the immutable raw-data directories.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.metrics import silhouette_score

from .cleaning import PROJECT_ROOT, clean_text, ensure_derived_output


DEFAULT_DATA = PROJECT_ROOT / "data/processed/jobs_cleaned.parquet"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/processed/clustering"
DEFAULT_REPORT = PROJECT_ROOT / "reports/clustering"

# The corpus contains multilingual vacancy templates. Removing common
# function words makes cluster labels less likely to be driven by boilerplate
# language rather than skills, titles and categories.
CLUSTER_STOP_WORDS = set(ENGLISH_STOP_WORDS) | {
    "und", "mit", "du", "wir", "fur", "für", "der", "die", "das", "von", "zu", "im", "ist",
    "para", "em", "que", "en", "la", "las", "los", "ou", "como", "con", "por", "una", "um",
    "uns", "bei", "oder", "deine", "auf", "ein", "eine", "einer", "einem", "diese", "dieser", "nicht", "auch",
    "bewerbung", "bewerbungen", "initiativbewerbung", "initiativbewerbungen", "offene", "abteilungen",
    "remote", "fully", "job", "jobs", "role", "roles", "work", "working", "experience", "opportunity", "upto", "hourly", "usd", "hr", "salary", "pay",
    "candidate", "candidates", "team", "company", "apply", "hiring", "position", "positions",
}


def _value(row: pd.Series, name: str) -> str:
    value = row.get(name, "")
    return "" if pd.isna(value) else str(value)


def build_cluster_text(df: pd.DataFrame) -> List[str]:
    """Build a weighted, human-readable text representation for each job."""
    texts: List[str] = []
    for _, row in df.iterrows():
        title = _value(row, "job_title")
        skills = _value(row, "skills_normalized").replace("|", " ")
        category = _value(row, "job_category")
        broad = _value(row, "broad_category")
        description = _value(row, "description_clean") or _value(row, "job_description")
        # Repetition provides a transparent weighting without introducing a
        # second opaque feature-engineering pipeline.
        texts.append(
            " ".join(
                [
                    title,
                    title,
                    title,
                    skills,
                    skills,
                    skills,
                    category,
                    category,
                    broad,
                    broad,
                    description,
                ]
            )
        )
    return texts


def fit_text_matrix(texts: Sequence[str]) -> Tuple[TfidfVectorizer, Any]:
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        stop_words=sorted(CLUSTER_STOP_WORDS),
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.98,
        max_features=8000,
        sublinear_tf=True,
        dtype=np.float64,
    )
    return vectorizer, vectorizer.fit_transform(texts)


def elbow_k(inertias: Dict[int, float]) -> int:
    """Return a reproducible elbow proxy using the largest second difference."""
    ks = sorted(inertias)
    if len(ks) < 3:
        return ks[0]
    scores: Dict[int, float] = {}
    for index in range(1, len(ks) - 1):
        previous, current, following = ks[index - 1 : index + 2]
        first_drop = inertias[previous] - inertias[current]
        second_drop = inertias[current] - inertias[following]
        scores[current] = first_drop - second_drop
    return max(scores, key=scores.get)


def evaluate_k_values(
    matrix: Any,
    k_values: Iterable[int],
    silhouette_sample_size: int = 4000,
) -> Tuple[pd.DataFrame, Dict[int, KMeans]]:
    rows: List[Dict[str, float]] = []
    fitted: Dict[int, KMeans] = {}
    for k in k_values:
        model = KMeans(n_clusters=int(k), n_init=10, max_iter=120, random_state=42)
        labels = model.fit_predict(matrix)
        sample_size = min(silhouette_sample_size, matrix.shape[0])
        score = silhouette_score(
            matrix,
            labels,
            sample_size=sample_size,
            random_state=42,
            metric="cosine",
        )
        rows.append({"k": int(k), "inertia": float(model.inertia_), "silhouette_score": float(score)})
        fitted[int(k)] = model
    return pd.DataFrame(rows), fitted


def _split_terms(value: Any, separator: str = "|") -> List[str]:
    return [part.strip() for part in str(value or "").split(separator) if part.strip()]


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]+", "_", value).strip("_") or "cluster"


def business_name(broad: str, terms: Sequence[str], index: int) -> str:
    joined = " ".join(terms).lower()
    if any(term in joined for term in ("bewerbung", "offene bewerbung", "initiativbewerbung")):
        return "开放申请与多职能岗位"
    if any(term in joined for term in ("localization", "translation", "translator", "multilingual", "language")):
        return "多语言与本地化岗位"
    if broad == "Data Science":
        if any(term in joined for term in ("machine learning", "deep learning", "ai", "model")):
            return "机器学习与人工智能岗位"
        if any(term in joined for term in ("analytics", "analyst", "sql", "tableau", "bi")):
            return "数据分析与商业智能岗位"
        return "数据科学与研究岗位"
    if broad == "Engineering":
        if any(term in joined for term in ("sap", "windchill", "innovation", "oracle", "erp")):
            return "企业应用与技术创新岗位"
        if any(term in joined for term in ("devops", "cloud", "kubernetes", "terraform", "infrastructure")):
            return "云平台与 DevOps 工程岗位"
        if any(term in joined for term in ("frontend", "react", "javascript", "web")):
            return "前端与 Web 开发岗位"
        if any(term in joined for term in ("backend", "api", "python", "java", "software")):
            return "后端与软件工程岗位"
        return "软件与技术工程岗位"
    labels = {
        "Sales": "销售与业务拓展岗位",
        "Operations": "运营与项目管理岗位",
        "Marketing": "市场与增长岗位",
        "Customer Service": "客户支持与成功岗位",
        "Healthcare": "医疗健康岗位",
        "Finance": "金融与会计岗位",
        "Product": "产品管理岗位",
        "Design": "设计与用户体验岗位",
        "Human Resources": "人力资源与招聘岗位",
        "Legal": "法律与合规岗位",
        "Education": "教育与培训岗位",
        "Other": "跨职能与其他岗位",
    }
    return labels.get(broad, f"{broad or '未分类'}岗位组 {index + 1}")


def summarize_clusters(
    df: pd.DataFrame,
    labels: Sequence[int],
    model: KMeans,
    feature_names: Sequence[str],
    top_n: int = 10,
    feature_matrix: Any = None,
) -> List[Dict[str, Any]]:
    frame = df.copy().reset_index(drop=True)
    frame["cluster_id"] = list(map(int, labels))
    centers = model.cluster_centers_
    summaries: List[Dict[str, Any]] = []
    used_names: Dict[str, int] = {}
    for cluster_id in sorted(frame["cluster_id"].unique()):
        subset = frame[frame["cluster_id"] == cluster_id]
        if feature_matrix is not None:
            # Explain a reduced-space K-Means model with the original TF-IDF
            # centroid, keeping the displayed terms interpretable.
            center = np.asarray(feature_matrix[subset.index].mean(axis=0)).ravel()
        else:
            center = centers[int(cluster_id)]
        top_indices = np.argsort(center)[::-1]
        terms: List[str] = []
        for feature_index in top_indices:
            candidate = str(feature_names[feature_index])
            tokens = candidate.split()
            if not any(token not in CLUSTER_STOP_WORDS and len(token) > 2 for token in tokens):
                continue
            if candidate not in terms:
                terms.append(candidate)
            if len(terms) >= top_n:
                break
        broad_counts = subset["broad_category"].fillna("Other").value_counts()
        dominant_broad = str(broad_counts.index[0]) if not broad_counts.empty else "Other"
        title_counts = subset["job_title"].fillna("").replace("", np.nan).dropna().value_counts().head(top_n)
        title_terms = [str(value) for value in title_counts.index[:5]]
        name = business_name(dominant_broad, list(terms) + title_terms, int(cluster_id))
        used_names[name] = used_names.get(name, 0) + 1
        if used_names[name] > 1:
            name = f"{name}（组 {used_names[name]}）"
        skill_counts: Dict[str, int] = {}
        for value in subset["skills_normalized"].fillna(""):
            for skill in _split_terms(value):
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        top_skills = [
            {"skill": skill, "count": int(count)}
            for skill, count in sorted(skill_counts.items(), key=lambda item: (-item[1], item[0]))[:top_n]
        ]
        categories = subset["broad_category"].fillna("Other").value_counts().head(5).to_dict()
        job_categories = subset["job_category"].fillna("").replace("", np.nan).dropna().value_counts().head(8)
        summaries.append(
            {
                "cluster_id": int(cluster_id),
                "business_name": name,
                "job_count": int(len(subset)),
                "share": round(float(len(subset) / len(frame)), 4),
                "dominant_broad_category": dominant_broad,
                "category_distribution": {str(k): int(v) for k, v in categories.items()},
                "top_job_categories": [{"category": str(k), "count": int(v)} for k, v in job_categories.items()],
                "top_terms": terms,
                "top_titles": [{"title": str(k), "count": int(v)} for k, v in title_counts.items()],
                "top_skills": top_skills,
                "interpretation": (
                    f"该类包含 {len(subset):,} 个岗位，主要属于 {dominant_broad}。"
                    f" 高频文本特征包括：{'、'.join(terms[:5])}。"
                    " 名称依据主类别与高权重词生成，便于业务阅读。"
                ),
            }
        )
    return summaries


def _write_json(path: Path, payload: Any) -> None:
    ensure_derived_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plot_k_diagnostics(metrics: pd.DataFrame, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    plt.plot(metrics["k"], metrics["inertia"], marker="o", color="#0B6E69")
    plt.xticks(metrics["k"])
    plt.xlabel("Number of clusters K")
    plt.ylabel("Within-cluster inertia")
    plt.title("K-Means elbow diagnostic")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(report_dir / "elbow_plot.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(metrics["k"], metrics["silhouette_score"], marker="o", color="#C4572D")
    plt.xticks(metrics["k"])
    plt.xlabel("Number of clusters K")
    plt.ylabel("Silhouette score")
    plt.title("K-Means silhouette diagnostic")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(report_dir / "silhouette_plot.png", dpi=160)
    plt.close()


def plot_embedding(matrix: Any, labels: Sequence[int], report_dir: Path, coordinates: Any = None) -> None:
    reducer = None if coordinates is not None else TruncatedSVD(n_components=2, random_state=42)
    coordinates = coordinates if coordinates is not None else reducer.fit_transform(matrix)
    plt.figure(figsize=(9, 7))
    scatter = plt.scatter(
        coordinates[:, 0],
        coordinates[:, 1],
        c=np.asarray(labels),
        cmap="tab20",
        s=8,
        alpha=0.55,
        linewidths=0,
    )
    plt.xlabel("SVD component 1")
    plt.ylabel("SVD component 2")
    plt.title("Job-cluster projection (TruncatedSVD / sparse PCA)")
    plt.colorbar(scatter, label="cluster_id")
    plt.tight_layout()
    plt.savefig(report_dir / "cluster_scatter_pca.png", dpi=160)
    plt.close()


def write_report(
    report_path: Path,
    metrics: pd.DataFrame,
    selected_k: int,
    elbow: int,
    silhouette_k: int,
    summaries: Sequence[Dict[str, Any]],
    sample_size: int,
) -> None:
    lines = [
        "# 岗位聚类分析报告",
        "",
        "## 1. 聚类目标",
        "",
        f"本分析使用清洗后的 {sample_size:,} 条全球远程岗位，发现标题、技能、类别和描述中的岗位群组。结果用于岗位浏览、检索和人岗匹配解释，不代表劳动力市场中的唯一职业分类。",
        "",
        "## 2. 特征与方法",
        "",
        "- 文本字段：`job_title`、`skills_normalized`、`job_category`、`broad_category`、`description_clean`。",
        "- 采用 TF-IDF 词与二元短语，标题和技能重复三次、类别重复两次，以表达业务上更重要的信号。",
        "- 主模型为 K-Means：先将 TF-IDF 矩阵用 TruncatedSVD 压缩到 50 维，再在低维表示上聚类；原始 TF-IDF 中心用于提取可解释的高权重词。二维图使用同一 SVD 表示。",
        "- 轮廓系数在最多 4,000 条固定随机样本上计算，降低大样本距离计算成本。",
        "",
        "## 3. K 值选择",
        "",
        f"肘部代理选择 K={elbow}，轮廓系数最高为 K={silhouette_k}，本次最终模型选择 K={selected_k}。完整数值见 `k_selection_metrics.csv`，图见 `elbow_plot.png` 与 `silhouette_plot.png`。",
        "",
        "| K | Inertia | Silhouette |",
        "| ---: | ---: | ---: |",
    ]
    for row in metrics.itertuples(index=False):
        lines.append(f"| {int(row.k)} | {row.inertia:,.2f} | {row.silhouette_score:.4f} |")
    lines += ["", "## 4. 聚类结果与业务命名", ""]
    for item in summaries:
        lines += [
            f"### Cluster {item['cluster_id']} {item['business_name']}",
            "",
            f"岗位数量：{item['job_count']:,}（{item['share']:.1%}）；主类别：{item['dominant_broad_category']}。",
            f"高频标题：{'、'.join(x['title'] for x in item['top_titles'][:5]) or '无'}。",
            f"主要技能：{'、'.join(x['skill'] for x in item['top_skills'][:8]) or '无'}。",
            f"细分类别：{'、'.join(x['category'] for x in item['top_job_categories'][:5]) or '无'}。",
            f"解释：{item['interpretation']}",
            "",
        ]
    lines += [
        "## 5. 偏差与局限",
        "",
        "样本明显偏向 Engineering 与 Data Science，聚类边界会受到平台岗位结构和原始类别字段的影响。K-Means 假设簇在 TF-IDF 空间中近似凸形，难以表达跨类别岗位；业务名称是基于高权重词的解释层，不是人工职业标准。后续可以对 Engineering 和 Data Science 分层聚类，并用人工抽样复核名称稳定性。",
        "",
        "## 6. 可追溯输出",
        "",
        "标签数据保存在 `data/processed/clustering/job_clusters.parquet`，每条记录保留 `job_id`、`source_url`、`crawl_time` 与 `data_origin`。",
        "",
    ]
    ensure_derived_output(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run_clustering(
    data_path: Path = DEFAULT_DATA,
    output_dir: Path = DEFAULT_OUTPUT,
    report_dir: Path = DEFAULT_REPORT,
    k_min: int = 3,
    k_max: int = 8,
) -> Dict[str, Any]:
    df = pd.read_parquet(data_path)
    if df.empty:
        raise ValueError("cleaned job data is empty")
    texts = build_cluster_text(df)
    vectorizer, matrix = fit_text_matrix(texts)
    # K-Means is fitted on a compact dense projection to avoid numerical
    # instability in very high-dimensional sparse input. The original TF-IDF
    # matrix remains the explanation source for top terms.
    projection_components = min(50, max(2, matrix.shape[1] - 1))
    reducer = TruncatedSVD(
        n_components=projection_components,
        algorithm="arpack",
        random_state=42,
    )
    projected_matrix = reducer.fit_transform(matrix)
    metrics, fitted = evaluate_k_values(projected_matrix, range(k_min, k_max + 1))
    inertias = {int(row.k): float(row.inertia) for row in metrics.itertuples()}
    elbow = elbow_k(inertias)
    silhouette_k = int(metrics.loc[metrics["silhouette_score"].idxmax(), "k"])
    # Use the elbow as the baseline, then allow a clearly stronger silhouette
    # result to win. The report records both values so the choice is auditable.
    elbow_score = float(metrics.loc[metrics["k"].eq(elbow), "silhouette_score"].iloc[0])
    silhouette_score_max = float(metrics["silhouette_score"].max())
    selected_k = silhouette_k if silhouette_score_max - elbow_score >= 0.003 else elbow
    model = fitted[selected_k]
    labels = model.labels_.astype(int)
    feature_names = vectorizer.get_feature_names_out()
    summaries = summarize_clusters(df, labels, model, feature_names, feature_matrix=matrix)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    labeled = df.copy()
    labeled["cluster_id"] = labels
    labeled.to_parquet(output_dir / "job_clusters.parquet", index=False)
    labeled[["job_id", "job_title", "company_name", "broad_category", "skills_normalized", "source_url", "crawl_time", "data_origin", "cluster_id"]].to_csv(
        output_dir / "job_clusters.csv", index=False
    )
    metrics.to_csv(report_dir / "k_selection_metrics.csv", index=False)
    _write_json(report_dir / "k_selection_metrics.json", metrics.to_dict(orient="records"))
    _write_json(report_dir / "cluster_summary.json", summaries)
    pd.DataFrame(
        [
            {
                "cluster_id": item["cluster_id"],
                "business_name": item["business_name"],
                "job_count": item["job_count"],
                "share": item["share"],
                "dominant_broad_category": item["dominant_broad_category"],
                "top_titles": " | ".join(x["title"] for x in item["top_titles"][:5]),
                "top_skills": " | ".join(x["skill"] for x in item["top_skills"][:8]),
                "top_job_categories": " | ".join(x["category"] for x in item["top_job_categories"][:5]),
            }
            for item in summaries
        ]
    ).to_csv(report_dir / "cluster_summary.csv", index=False)
    plot_k_diagnostics(metrics, report_dir)
    plot_embedding(matrix, labels, report_dir, coordinates=reducer.transform(matrix)[:, :2])
    write_report(report_dir / "clustering_report.md", metrics, selected_k, elbow, silhouette_k, summaries, len(df))

    manifest = {
        "data_path": str(data_path),
        "records": int(len(df)),
        "feature_count": int(matrix.shape[1]),
        "projection_components": int(projection_components),
        "candidate_k": [int(value) for value in range(k_min, k_max + 1)],
        "elbow_k": int(elbow),
        "silhouette_k": int(silhouette_k),
        "selected_k": int(selected_k),
        "random_state": 42,
    }
    _write_json(report_dir / "clustering_manifest.json", manifest)
    return {"manifest": manifest, "metrics": metrics, "summaries": summaries}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run interpretable K-Means clustering on cleaned jobs")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--k-min", type=int, default=3)
    parser.add_argument("--k-max", type=int, default=8)
    args = parser.parse_args()
    result = run_clustering(args.data, args.output_dir, args.report_dir, args.k_min, args.k_max)
    print(json.dumps(result["manifest"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
