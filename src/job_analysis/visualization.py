"""Generate reproducible business visualizations and written insights."""

import argparse
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import font_manager
from matplotlib.dates import DateFormatter, DayLocator

from .cleaning import PROJECT_ROOT, ensure_derived_output


INPUT_PATH = PROJECT_ROOT / "data/processed/jobs_cleaned.parquet"
FIGURE_DIR = PROJECT_ROOT / "reports/figures"
REPORT_PATH = PROJECT_ROOT / "reports/visualization_report.md"

PALETTE = ["#216869", "#49A078", "#D9A441", "#D1495B", "#5F6CAF", "#7678ED", "#F18701", "#6D6875"]


def configure_style() -> None:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            font_manager.fontManager.addfont(candidate)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=candidate).get_name()
            break
    plt.rcParams.update(
        {
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "#F7F8F6",
            "axes.edgecolor": "#D6D8D3",
            "axes.titleweight": "bold",
            "axes.titlesize": 15,
            "axes.labelsize": 11,
            "font.size": 10,
        }
    )
    sns.set_theme(style="whitegrid", font=plt.rcParams["font.family"], rc={"axes.unicode_minus": False})


def save_figure(fig: plt.Figure, path: Path) -> None:
    ensure_derived_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def top_categories(df: pd.DataFrame) -> Tuple[str, str]:
    counts = df["broad_category"].value_counts().head(12).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6.4))
    colors = [PALETTE[index % len(PALETTE)] for index in range(len(counts))]
    ax.barh(counts.index, counts.values, color=colors)
    ax.set(title="全球远程岗位宽类分布（Top 12）", xlabel="岗位数", ylabel="岗位宽类")
    ax.bar_label(ax.containers[0], fmt="%d", padding=4)
    ax.grid(axis="y", visible=False)
    save_figure(fig, FIGURE_DIR / "01_broad_category_distribution.png")
    top_name, top_count = counts.index[-1], int(counts.iloc[-1])
    insight = f"{top_name} 为最大岗位宽类，共 {top_count:,} 条，占清洗后岗位的 {top_count / len(df):.1%}。这说明远程市场样本的职位结构明显集中，后续匹配与聚类应按类别分层评估，避免大类淹没小类。"
    return "01_broad_category_distribution.png", insight


def salary_distribution(df: pd.DataFrame) -> Tuple[str, str]:
    salary = df["salary_avg_usd_annual_winsorized"].dropna() / 1000
    fig, ax = plt.subplots(figsize=(10, 5.8))
    sns.histplot(salary, bins=35, color=PALETTE[0], edgecolor="white", ax=ax)
    median = float(salary.median())
    ax.axvline(median, color=PALETTE[3], linewidth=2, label=f"中位数 ${median:,.0f}k")
    ax.set(title="已披露 USD 岗位的年薪分布（P1/P99 缩尾）", xlabel="年薪中点（千 USD）", ylabel="岗位数")
    ax.legend(frameon=False)
    save_figure(fig, FIGURE_DIR / "02_usd_salary_distribution.png")
    insight = f"共有 {len(salary):,} 条岗位具备可比较的非异常 USD 年薪，年薪中点中位数为 ${median * 1000:,.0f}。由于仅覆盖主动披露 USD 薪资的岗位，该结果反映的是透明薪资子样本，不能外推到全部远程岗位。"
    return "02_usd_salary_distribution.png", insight


def salary_by_seniority(df: pd.DataFrame) -> Tuple[str, str]:
    order = ["Entry-Level", "Mid-Level", "Senior", "Manager", "Director", "Executive"]
    frame = df.loc[df["salary_avg_usd_annual_winsorized"].notna(), ["experience_level_primary", "salary_avg_usd_annual_winsorized"]].copy()
    frame["salary_k"] = frame["salary_avg_usd_annual_winsorized"] / 1000
    present = [level for level in order if level in set(frame["experience_level_primary"])]
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(data=frame, x="experience_level_primary", y="salary_k", order=present, hue="experience_level_primary", palette=PALETTE[: len(present)], legend=False, showfliers=False, ax=ax)
    ax.set(title="职级与 USD 年薪的关系", xlabel="来源职级", ylabel="年薪中点（千 USD）")
    ax.tick_params(axis="x", rotation=20)
    save_figure(fig, FIGURE_DIR / "03_salary_by_seniority.png")
    medians = frame.groupby("experience_level_primary")["salary_k"].median().sort_values(ascending=False)
    highest, value = medians.index[0], float(medians.iloc[0])
    insight = f"在有 USD 薪资的岗位中，{highest} 的年薪中位数最高（约 ${value * 1000:,.0f}）。箱体仍有明显重叠，说明职级不是薪资的唯一解释变量，类别、地区限制和用工方式也应纳入判断。"
    return "03_salary_by_seniority.png", insight


def top_skills(df: pd.DataFrame) -> Tuple[str, str]:
    counts: Counter = Counter()
    for value in df["skills_normalized"].fillna(""):
        counts.update(part.strip() for part in str(value).split("|") if part.strip())
    top = counts.most_common(20)
    labels = [name for name, _ in reversed(top)]
    values = [count for _, count in reversed(top)]
    fig, ax = plt.subplots(figsize=(10, 7.5))
    ax.barh(labels, values, color=PALETTE[1])
    ax.set(title="远程岗位技能标签需求（Top 20）", xlabel="出现岗位数", ylabel="技能标签")
    ax.bar_label(ax.containers[0], fmt="%d", padding=3, fontsize=8)
    ax.grid(axis="y", visible=False)
    save_figure(fig, FIGURE_DIR / "04_top_skills.png")
    first, first_count = top[0]
    insight = f"技能标签中 `{first}` 出现最多（{first_count:,} 条）。技能标签来自平台分类体系，包含角色词与技术词，适合用于召回和聚类，但在人岗匹配中还需建立同义词归一化，避免把类别名称直接视为候选人技能。"
    return "04_top_skills.png", insight


def description_quality(df: pd.DataFrame) -> Tuple[str, str]:
    frame = df[["description_length", "quality_score"]].copy()
    frame["length_bin"] = pd.qcut(frame["description_length"], q=10, duplicates="drop")
    grouped = frame.groupby("length_bin", observed=True).agg(description_length=("description_length", "median"), quality_score=("quality_score", "mean"))
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.plot(grouped["description_length"], grouped["quality_score"], marker="o", linewidth=2.5, color=PALETTE[4])
    ax.set(title="岗位描述长度与信息质量分", xlabel="分位组描述长度中位数（字符）", ylabel="平均信息质量分")
    ax.set_ylim(max(0, grouped["quality_score"].min() - 5), min(100, grouped["quality_score"].max() + 5))
    save_figure(fig, FIGURE_DIR / "05_description_length_quality.png")
    correlation = float(df["description_length"].corr(df["quality_score"], method="spearman"))
    insight = f"描述长度与规则信息质量分的 Spearman 相关系数为 {correlation:.2f}。长度只贡献有限分值，过长文本不自动等于高质量；招聘方更应补足薪资、技能和职责结构，而不是单纯增加篇幅。"
    return "05_description_length_quality.png", insight


def posting_trend(df: pd.DataFrame) -> Tuple[str, str]:
    dates = pd.to_datetime(df["publish_date"], errors="coerce", utc=True).dt.date
    counts = dates.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.plot(pd.to_datetime(counts.index), counts.values, color=PALETTE[3], linewidth=2)
    ax.fill_between(pd.to_datetime(counts.index), counts.values, color=PALETTE[3], alpha=0.14)
    ax.set(title="样本岗位发布日期趋势", xlabel="发布日期（UTC）", ylabel="岗位数")
    ax.xaxis.set_major_locator(DayLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%m-%d"))
    fig.autofmt_xdate(rotation=25)
    save_figure(fig, FIGURE_DIR / "06_posting_date_trend.png")
    peak_date, peak_count = counts.idxmax(), int(counts.max())
    start, end = counts.index.min(), counts.index.max()
    insight = f"样本发布日期覆盖 {start} 至 {end}，峰值为 {peak_date} 的 {peak_count:,} 条。该趋势同时受 API 排序和截取窗口影响，更适合描述本次采集快照，不应解释为完整市场新增岗位走势。"
    return "06_posting_date_trend.png", insight


def quality_distribution(df: pd.DataFrame) -> Tuple[str, str]:
    level_order = ["Low", "Medium", "High"]
    counts = df["quality_level"].value_counts().reindex(level_order, fill_value=0)
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    bars = ax.bar(counts.index, counts.values, color=[PALETTE[3], PALETTE[2], PALETTE[1]])
    ax.bar_label(bars, labels=[f"{value:,}\n({value / len(df):.1%})" for value in counts.values], padding=4)
    ax.set(title="岗位信息质量等级分布", xlabel="规则等级", ylabel="岗位数", ylim=(0, max(counts.values) * 1.24))
    ax.set_title("岗位信息质量等级分布", pad=14)
    ax.grid(axis="x", visible=False)
    save_figure(fig, FIGURE_DIR / "07_quality_level_distribution.png")
    high = int(counts["High"])
    insight = f"固定规则下，高信息质量岗位为 {high:,} 条（{high / len(df):.1%}）。该比例主要反映信息披露完整性，尤其是薪资透明度，不能等同于真实工作质量或企业信誉。"
    return "07_quality_level_distribution.png", insight


def write_report(df: pd.DataFrame, results: List[Tuple[str, str]]) -> None:
    salary_disclosure = float(df["salary_raw"].fillna("").astype(str).str.strip().ne("").mean())
    it_data_share = float(df["is_it_data_role"].mean())
    sections = []
    titles = [
        "岗位类别结构",
        "USD 年薪分布",
        "职级与薪资",
        "技能需求",
        "描述长度与质量分",
        "发布日期趋势",
        "信息质量等级",
    ]
    for index, ((filename, insight), title) in enumerate(zip(results, titles), start=1):
        sections.append(f"## {index}. {title}\n\n![{title}](figures/{filename})\n\n{insight}")
    section_text = "\n\n".join(sections)
    text = f"""# 可视化分析报告

## 数据口径

报告基于 {len(df):,} 条去重后的全球远程岗位。全部岗位的 `city` 均为 `Remote`；`district` 是申请地区限制。薪资披露率为 {salary_disclosure:.1%}，工程/数据类岗位占 {it_data_share:.1%}。跨币种不换算，金额图只分析可解析、非异常的 USD 年薪，并使用 P1/P99 缩尾值。

{section_text}

## 综合结论

远程岗位样本的岗位类别、技能和薪资披露程度存在明显差异。对求职者而言，推荐系统应同时展示类别相关性、技能缺口和信息透明度；对招聘方而言，明确薪资、职责结构和技能要求能直接提升岗位信息质量。由于数据是一次 API 时间窗口快照，所有趋势结论都应限定在本样本内。
"""
    ensure_derived_output(REPORT_PATH)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text, encoding="utf-8")


def run(input_path: Path = INPUT_PATH) -> List[Tuple[str, str]]:
    configure_style()
    df = pd.read_parquet(input_path)
    results = [
        top_categories(df),
        salary_distribution(df),
        salary_by_seniority(df),
        top_skills(df),
        description_quality(df),
        posting_trend(df),
        quality_distribution(df),
    ]
    write_report(df, results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate week-one business visualizations")
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    args = parser.parse_args()
    results = run(args.input)
    print(f"Generated {len(results)} figures and {REPORT_PATH}")


if __name__ == "__main__":
    main()
