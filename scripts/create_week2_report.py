"""Create the Week 2 comparison report and M2 presentation outline."""

from __future__ import annotations

import json
import argparse
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

DOCX_AVAILABLE = True
try:
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor
except Exception:
    # Markdown and outline generation do not require python-docx.
    DOCX_AVAILABLE = False


ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "reports/modeling/model_metrics.csv"
CLUSTER_MANIFEST = ROOT / "reports/clustering/clustering_manifest.json"
CLUSTER_SUMMARY = ROOT / "reports/clustering/cluster_summary.json"
RAG_MANIFEST = ROOT / "data/processed/rag/index_manifest.json"
RAG_TESTS = ROOT / "reports/rag/retrieval_tests.json"
RAG_EVAL = ROOT / "reports/rag/rag_eval_summary.json"
TFIDF_BASELINE_EVAL = ROOT / "reports/rag_tfidf_baseline/rag_eval_summary.json"
AGENT_REAL = ROOT / "reports/agent/real_demo_output.json"
AGENT_FALLBACK = ROOT / "reports/agent/demo_output.json"
DOCX_OUT = ROOT / "submit/多模型对比分析报告.docx"
MD_OUT = ROOT / "reports/multi_model_comparison.md"
OUTLINE_OUT = ROOT / "submit/中期汇报二PPT大纲.md"
REPORT_DATE = "2026-09-17"


def _set_cell_shading(cell: Any, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)


def _set_run_font(run: Any, latin: str = "Arial", east_asia: str = "STHeiti") -> None:
    run.font.name = latin
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), latin)
    rfonts.set(qn("w:hAnsi"), latin)
    rfonts.set(qn("w:eastAsia"), east_asia)


def _remove_paragraph_borders(paragraph: Any) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    borders = ppr.find(qn("w:pBdr"))
    if borders is not None:
        ppr.remove(borders)


def _set_cell_borders(cell: Any, color: str = "D9D9D9") -> None:
    properties = cell._tc.get_or_add_tcPr()
    borders = properties.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        properties.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def _format_table(table: Any, header_fill: str = "1F4E5F") -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for row_index, row in enumerate(table.rows):
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_cell_borders(cell)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(2)
                for run in paragraph.runs:
                    _set_run_font(run)
                    run.font.size = Pt(9)
                    if row_index == 0:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
            if row_index == 0:
                _set_cell_shading(cell, header_fill)
            elif row_index % 2 == 0:
                _set_cell_shading(cell, "F3F6F7")


def _add_table(doc: Document, headers: List[str], rows: Iterable[Iterable[Any]]) -> Any:
    table = doc.add_table(rows=1, cols=len(headers))
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = str(header)
    for values in rows:
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].text = str(value)
    _format_table(table)
    doc.add_paragraph()
    return table


def _add_figure(doc: Document, path: Path, caption: str, width: float = 6.2) -> None:
    """Insert an existing local analysis figure with a traceable caption."""
    if not path.exists():
        return
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(3)
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.add_run().add_picture(str(path), width=Inches(width))
    caption_paragraph = doc.add_paragraph()
    caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_paragraph.paragraph_format.space_after = Pt(6)
    caption = caption_paragraph.add_run(caption)
    _set_run_font(caption)
    caption.font.size = Pt(8.5)
    caption.font.italic = True
    caption.font.color.rgb = RGBColor(82, 96, 109)


def _load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _tool_chain(payload: Dict[str, Any]) -> str:
    tools = [call.get("tool", "") for call in payload.get("tool_calls", []) if call.get("tool")]
    return " -> ".join(tools)


def _pct(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except Exception:
        return str(value)


def build_markdown() -> str:
    metrics = pd.read_csv(METRICS)
    manifest = _load_json(CLUSTER_MANIFEST, {})
    summaries = _load_json(CLUSTER_SUMMARY, [])
    rag_manifest = _load_json(RAG_MANIFEST, {})
    rag_eval = _load_json(RAG_EVAL, {})
    rag_tests = _load_json(RAG_TESTS, [])
    tfidf_eval = _load_json(TFIDF_BASELINE_EVAL, {})
    agent_real = _load_json(AGENT_REAL, {})
    agent_fallback = _load_json(AGENT_FALLBACK, {})
    chunking = rag_manifest.get("chunking", {})
    embedding = rag_manifest.get("embedding", {})
    vector_store = rag_manifest.get("vector_store", {})
    question_count = rag_eval.get("question_count", len(rag_tests))
    metric_text = "; ".join(
        f"{row.model}: F1={row.f1:.4f}, ROC-AUC={row.roc_auc:.4f}" for row in metrics.itertuples()
    )
    lines = [
        "# 多模型对比分析报告",
        "",
        f"生成日期：{REPORT_DATE}。本报告比较岗位信息质量评分、人岗匹配、岗位聚类、RAG 检索和 Agent 工作流。所有数字来自当前项目输出，不虚构指标。",
        "",
        "## 1. 统一数据底座",
        "",
        "- 数据：清洗后的 `data/processed/jobs_cleaned.parquet`，12,000 条全球远程岗位。",
        "- 追溯：岗位记录保留 `job_id`、`source_url`、`crawl_time`、`data_origin`；`city=Remote` 保持不变。",
        "- 约束：岗位质量分表示岗位信息透明度与完整度；匹配分表示排序参考，不是企业信誉或录用概率。",
        "",
        "## 2. 横向比较",
        "",
        "| 模块 | 业务目标 | 输入与核心算法 | 输出与评价 | 当前状态 | 局限 |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| 岗位质量评分 | 衡量岗位信息完整度和透明度 | 数值、类别和文本 TF-IDF；Logistic Regression、Linear SVM、Random Forest、XGBoost | {metric_text}；XGBoost 最佳 | 已完成 | 规则代理标签，不是雇主信誉；文本特征可能带来来源偏差 |",
        "| 人岗匹配 | 根据简历对岗位排序并解释技能缺口 | TF-IDF + 余弦相似度；技能 55%、类别 20%、经验 15%、地点 10% | `match_score`、分项分数、命中/缺失技能、解释和来源链接 | 已完成并有演示 | 技能词典覆盖有限；没有人工招聘结果标签；薪资仅展示 |",
        f"| 岗位聚类 | 发现岗位群组，辅助浏览和解释 | 加权 TF-IDF + K-Means；肘部和轮廓系数检查 K | K={manifest.get('selected_k', '')}；轮廓最高 K={manifest.get('silhouette_k', '')}；{len(summaries)} 个业务命名聚类 | 已完成 | Engineering/Data Science 样本偏多；K-Means 边界和自动命名需要人工复核 |",
        f"| RAG 检索 | 对自然语言问题召回可追溯岗位 | 正式方案：FAISS IndexFlatIP + `{embedding.get('model', 'BAAI/bge-small-zh-v1.5')}`；TF-IDF 仅作历史基线 | 主索引 {chunking.get('chunk_count', '')} Chunk；{question_count} 题；Query Hit@3={_pct(rag_eval.get('query_hit_rate_at_3'))}；来源覆盖 {_pct(rag_eval.get('source_trace_coverage'))} | 正式 RAG 已完成 | 金标准是结构化规则，不是人工标注真实 Recall；跨语言表达仍有失败题 |",
        f"| Agent 工作流 | 将检索、评分、匹配、聚类组合成可交互工具 | OpenAI-compatible Function Calling；工具在本地执行；无凭据时回退规则路由 | 真实演示 `model_call=true`（{_tool_chain(agent_real)}）；fallback `model_call=false` | 真实模型版已完成 | 模型服务延迟和兼容性会影响现场体验；底层工具仍受技能词典与字段限制 |",
        "",
        "## 3. 真实模型结果",
        "",
        "| 模型 | Accuracy | Precision | Recall | F1 | ROC-AUC |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in metrics.itertuples():
        lines.append(
            f"| {row.model} | {row.accuracy:.4f} | {row.precision:.4f} | {row.recall:.4f} | {row.f1:.4f} | {row.roc_auc:.4f} |"
        )
    lines += [
        "",
        "XGBoost 在现有测试集上 F1=0.9140、ROC-AUC=0.9662，适合作为岗位信息质量评分的当前基线。该结果反映模型复现规则代理标签的能力，不能解读为录用成功率。",
        "",
        "## 4. 聚类结果",
        "",
        f"候选 K 为 {manifest.get('candidate_k', [])}。肘部代理为 K={manifest.get('elbow_k', '')}，轮廓系数最高为 K={manifest.get('silhouette_k', '')}，综合选择 K={manifest.get('selected_k', '')}。",
        "",
        "| Cluster | 业务名称 | 岗位数 | 主类别 | 主要技能 |",
        "| ---: | --- | ---: | --- | --- |",
    ]
    for item in summaries:
        skills = "、".join(x["skill"] for x in item["top_skills"][:5])
        lines.append(
            f"| {item['cluster_id']} | {item['business_name']} | {item['job_count']:,} | {item['dominant_broad_category']} | {skills} |"
        )
    lines += [
        "",
        "## 5. RAG 与 Agent 演示",
        "",
        (
            f"正式 RAG 使用 {vector_store.get('name', 'FAISS')} {vector_store.get('index_type', 'IndexFlatIP')} "
            f"与 Embedding `{embedding.get('model', 'BAAI/bge-small-zh-v1.5')}`（{embedding.get('dimension', 512)} 维）。"
            f"主索引按岗位介绍/职责/任职要求分区建块，Chunk={chunking.get('chunk_size', 1200)}、Overlap={chunking.get('chunk_overlap', 200)}，"
            f"共 {chunking.get('chunk_count', '')} 个 Chunk。测试问题 {question_count} 个，Top-k=3；"
            f"Query Hit@3={_pct(rag_eval.get('query_hit_rate_at_3'))}，Macro P@3={_pct(rag_eval.get('macro_precision_at_3'))}，"
            f"Macro MRR@3={_pct(rag_eval.get('macro_mrr_at_3'))}，来源字段完整率={_pct(rag_eval.get('source_trace_coverage'))}。"
            "金标准是可复现结构化条件，不是人工标注真实 Recall@k。检索日志位于 `reports/rag/retrieval_tests.json` 与 `reports/rag/rag_eval_summary.json`。"
        ),
        "",
        (
            f"TF-IDF 基线保留在 `reports/rag_tfidf_baseline/`：{tfidf_eval.get('test_question_count', 10)} 题、"
            f"Top-k={tfidf_eval.get('top_k', 3)}、预设条件可验证命中率={tfidf_eval.get('criterion_hit_rate_percent', '')}%。"
            "该基线只用于对比，不冒充 Embedding RAG，也不把 TF-IDF 说成深度学习。"
        ),
        "",
        (
            f"Agent 真实演示位于 `reports/agent/real_demo_output.json`：`agent_mode={agent_real.get('agent_mode')}`，"
            f"`model_call={agent_real.get('model_call')}`，protocol=`{agent_real.get('protocol')}`，"
            f"model=`{agent_real.get('model')}`，工具链 `{_tool_chain(agent_real)}`。"
            f"离线 fallback 位于 `reports/agent/demo_output.json`：`agent_mode={agent_fallback.get('agent_mode')}`，"
            f"`model_call={agent_fallback.get('model_call')}`，工具链 `{_tool_chain(agent_fallback)}`。"
            "可用工具为 `search_jobs`、`score_job`、`match_resume`、`cluster_summary`、`retrieve_jobs`。"
            "Prompt 版本记录位于 `docs/prompts/week2_agent_v1.md` 与 `reports/agent/prompt_versions.md`，"
            "Function Calling schema 位于 `reports/agent/function_schemas.json`。"
        ),
        "",
        "## 6. 结论与后续",
        "",
        "当前 Week 2 已形成从岗位聚类、正式 Embedding RAG 到真实模型 Agent 工具编排的可运行链路。后续应在不改变数据源的前提下补充人工聚类复核、技能词典扩充、前后端集成和真实服务稳定性测试；离线规则路由继续作为 fallback，并明确标注 `model_call=false`。",
        "",
    ]
    return "\n".join(lines)


def build_outline() -> str:
    manifest = _load_json(CLUSTER_MANIFEST, {})
    summaries = _load_json(CLUSTER_SUMMARY, [])
    rag_eval = _load_json(RAG_EVAL, {})
    rag_manifest = _load_json(RAG_MANIFEST, {})
    agent_real = _load_json(AGENT_REAL, {})
    agent_fallback = _load_json(AGENT_FALLBACK, {})
    cluster_lines = "；".join(
        f"Cluster {x['cluster_id']}：{x['business_name']}（{x['job_count']:,} 条）" for x in summaries
    )
    chunk_count = rag_manifest.get("chunking", {}).get("chunk_count", "")
    embedding_model = rag_manifest.get("embedding", {}).get("model", "BAAI/bge-small-zh-v1.5")
    return f"""# 中期汇报二 PPT 大纲

项目题目：基于全球远程招聘岗位大数据的岗位质量评分与人岗匹配研究  
汇报阶段：Week 2 / M2  
数据范围：12,000 条全球远程岗位，来源为 Himalayas 公开 Jobs API；不把 Remote 改写为具体城市。

## 第 1 页 研究链路与 M2 目标

- 讲稿：Week 2 将评分、匹配、聚类、正式 RAG 和真实模型 Agent 串成一条可演示链路。
- 现场动作：展示项目目录和五类业务问题。

## 第 2 页 数据底座与可追溯性

- 讲稿：展示 `jobs_cleaned.parquet`、12,000 条记录、0 条重复，以及 `job_id/source_url/crawl_time/data_origin`。
- 现场动作：抽查一条岗位来源链接。

## 第 3 页 人岗匹配演示

- 讲稿：输入 Python、SQL、4 年经验、美国远程的简历文本，使用既有公式计算匹配分。
- 公式：`skill_score=100*(0.70*cosine_similarity+0.30*matched_skill_count/job_skill_count)`；`match_score=0.55*skill_score+0.20*category_score+0.15*experience_score+0.10*location_score`。
- 现场动作：展示命中技能、缺失技能、分项分数、质量分和来源链接。

## 第 4 页 岗位聚类结果

- 讲稿：候选 K={manifest.get('candidate_k', [])}；肘部代理 K={manifest.get('elbow_k','')}，轮廓最高 K={manifest.get('silhouette_k','')}，综合选择 K={manifest.get('selected_k','')}。
- 现场动作：依次展示肘部图、轮廓图、降维散点图和业务命名摘要。
- 聚类摘要：{cluster_lines}

## 第 5 页 多模型对比

- 讲稿：评分模型比较 Logistic Regression、SVM、Random Forest、XGBoost；XGBoost 当前 F1=0.9140、ROC-AUC=0.9662。
- 同页对照：匹配是排序解释，聚类是无监督发现，RAG 是召回，Agent 是工具编排；不能混用同一评价指标。

## 第 6 页 RAG 检索问题与召回

- 讲稿：正式 RAG 为 FAISS + `{embedding_model}`，主索引 {chunk_count} Chunk，12 个测试问题；Query Hit@3={_pct(rag_eval.get('query_hit_rate_at_3'))}，来源覆盖 {_pct(rag_eval.get('source_trace_coverage'))}。
- 现场动作：检索一个真实问题，打开一条 `source_url`。
- 说明：TF-IDF 仅是历史基线；金标准是结构化规则，不是人工标注真实 Recall。

## 第 7 页 Agent 工具调用与工作流

- 讲稿：真实演示 `model_call={agent_real.get('model_call')}`、model=`{agent_real.get('model')}`，工具链 `{_tool_chain(agent_real)}`；同时保留 `model_call={agent_fallback.get('model_call')}` 的本地规则路由 fallback。
- 展示：Function Calling schema、Prompt 版本和 `reports/agent/real_demo_output.json`。

## 第 8 页 成果、问题与后续计划

- 已完成：匹配、聚类、四模型对比、FAISS+BGE RAG、真实模型 Agent、Prompt 版本。
- 当前问题：平台样本偏向 Engineering/Data Science；跨语言检索仍有失败题；聚类命名需人工抽查。
- Week 3：前后端集成、系统测试、部署与最终答辩材料。

## 现场演练顺序

1. 先展示数据和来源追溯。
2. 输入简历并展示匹配解释。
3. 打开聚类图和摘要。
4. 运行一个 RAG 问题并查看来源。
5. 运行 Agent 复合问题，说明真实模型调用与本地 fallback 边界。
"""


def build_docx(markdown: str) -> None:
    metrics = pd.read_csv(METRICS)
    manifest = _load_json(CLUSTER_MANIFEST, {})
    summaries = _load_json(CLUSTER_SUMMARY, [])
    rag_manifest = _load_json(RAG_MANIFEST, {})
    rag_eval = _load_json(RAG_EVAL, {})
    rag_tests = _load_json(RAG_TESTS, [])
    tfidf_eval = _load_json(TFIDF_BASELINE_EVAL, {})
    agent_real = _load_json(AGENT_REAL, {})
    agent_fallback = _load_json(AGENT_FALLBACK, {})
    k_metrics = pd.read_csv(ROOT / "reports/clustering/k_selection_metrics.csv")
    chunking = rag_manifest.get("chunking", {})
    embedding = rag_manifest.get("embedding", {})
    vector_store = rag_manifest.get("vector_store", {})
    question_count = rag_eval.get("question_count", len(rag_tests))
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    styles = doc.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10.5)
    for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        styles[style_name].font.name = "Arial"
        styles[style_name].font.color.rgb = RGBColor(0, 0, 0)
        style_rpr = styles[style_name]._element.get_or_add_rPr()
        style_fonts = style_rpr.find(qn("w:rFonts"))
        if style_fonts is None:
            style_fonts = OxmlElement("w:rFonts")
            style_rpr.append(style_fonts)
        style_fonts.set(qn("w:eastAsia"), "STHeiti")
    title_style_ppr = styles["Title"]._element.find(qn("w:pPr"))
    if title_style_ppr is not None:
        title_border = title_style_ppr.find(qn("w:pBdr"))
        if title_border is not None:
            title_style_ppr.remove(title_border)
    title = doc.add_paragraph(style="Title")
    _remove_paragraph_borders(title)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("多模型对比分析报告")
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run("基于全球远程招聘岗位大数据的岗位质量评分与人岗匹配研究\n").bold = True
    subtitle.add_run(f"Week 2 / M2 · {REPORT_DATE}")

    doc.add_heading("一、报告范围与统一数据底座", level=1)
    doc.add_paragraph("本报告围绕岗位质量评分、人岗匹配、岗位聚类、RAG 检索和 Agent 工具编排进行横向对比与调优说明。数据底座为 data/processed/jobs_cleaned.parquet 的 12,000 条全球远程岗位；每条结果均保留 job_id、source_url、crawl_time 和 data_origin。city 字段保持为 Remote。")
    doc.add_paragraph("语义边界：岗位质量分衡量岗位信息透明度与完整度；match_score 是岗位库内的排序参考分；二者均不是企业信誉或录用概率。聚类用于发现岗位群组，不产生分类准确率。RAG 负责可追溯召回；Agent 负责本地工具编排，不把工具结果改写为录用判断。")

    doc.add_heading("二、横向对比与评价口径", level=1)
    comparison_rows = [
        ["岗位质量评分", "用岗位字段完整度规则形成代理标签，比较四种分类器。", "数值/类别特征 + TF-IDF；Logistic Regression、Linear SVM、Random Forest、XGBoost。", "Accuracy、Precision、Recall、F1、ROC-AUC；可用特征重要性与规则追溯解释。"],
        ["人岗匹配", "把简历文本转为候选特征，对岗位进行 Top-k 排序。", "TF-IDF + 余弦相似度；技能、类别、经验、地点按 55/20/15/10 加权。", "输出 match_score、分项、命中/缺失技能和 source_url；无人工招聘结果标签，不虚构准确率。"],
        ["岗位聚类", "从标题、技能、类别、描述中发现可解释岗位群组。", "加权 TF-IDF -> TruncatedSVD(50) -> K-Means；在原始 TF-IDF 中提取中心词。", "Inertia、轮廓系数、PCA 二维分布、样本数量与业务命名；无监督任务不报告 F1。"],
        ["RAG 检索", "对自然语言问题召回可追溯岗位。", f"正式方案：{vector_store.get('name', 'FAISS')} {vector_store.get('index_type', 'IndexFlatIP')} + {embedding.get('model', 'BAAI/bge-small-zh-v1.5')}；TF-IDF 仅作历史基线。", f"{question_count} 题；Query Hit@3={_pct(rag_eval.get('query_hit_rate_at_3'))}；来源覆盖 {_pct(rag_eval.get('source_trace_coverage'))}；金标准为结构化规则。"],
        ["Agent 工作流", "把检索、评分、匹配、聚类组合成可交互工具链。", "OpenAI-compatible Function Calling；工具本地执行；无凭据时回退规则路由。", f"真实演示 model_call={agent_real.get('model_call')}；fallback model_call={agent_fallback.get('model_call')}；不虚构未发生的模型调用。"],
    ]
    _add_table(doc, ["模块", "业务目标与输入", "算法与输出", "评价、解释与局限"], comparison_rows)
    doc.add_paragraph("结论：五个模块服务的业务问题不同，不能把分类 F1、匹配排序分、聚类轮廓系数和 RAG Hit@k 混为同一指标。评分看监督学习指标；匹配看解释与来源；聚类看可分性与业务可读性；RAG 看可复现召回；Agent 看真实工具编排与 fallback 边界。")

    doc.add_page_break()
    doc.add_heading("三、岗位质量评分：四模型对比与调优结果", level=1)
    doc.add_paragraph("标签来自岗位信息完整度规则，模型学习的是代理标签而非雇主质量。所有结果均来自当前测试集；XGBoost 在现有四个模型中表现最佳，F1=0.9140，ROC-AUC=0.9662。")
    metric_rows = [[row.model, f"{row.accuracy:.4f}", f"{row.precision:.4f}", f"{row.recall:.4f}", f"{row.f1:.4f}", f"{row.roc_auc:.4f}"] for row in metrics.itertuples()]
    _add_table(doc, ["分类模型", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC"], metric_rows)
    _add_figure(doc, ROOT / "reports/modeling/model_comparison.png", "图 1  岗位质量评分的四模型指标对比（数据来源：reports/modeling/model_metrics.csv）。", width=5.8)
    doc.add_paragraph("模型选择解读：Logistic Regression 和 Linear SVM 是可解释的线性基线；Random Forest 可以刻画非线性关系；XGBoost 的综合 F1 与 ROC-AUC 最高，因此作为当前岗位信息质量评分的主模型。这个结论只表明其对规则代理标签的复现能力更强。")

    doc.add_heading("四、人岗匹配：简历输入、排序公式与解释", level=1)
    doc.add_paragraph("简历可由粘贴文本、UTF-8 文本文件或文本型 PDF 输入。PDF 使用 pypdf 的 PdfReader 逐页调用 page.extract_text()；扫描 PDF 没有文本层时会提示，当前版本不把 OCR 伪装成已实现功能。进入算法后，简历与岗位统一经过 clean_text、jieba 分词、技能别名归一化、经验和类别识别。")
    doc.add_paragraph("skill_score = 100 × [0.70 × cosine_similarity + 0.30 × matched_skill_count / job_skill_count]；match_score = 0.55 × skill_score + 0.20 × category_score + 0.15 × experience_score + 0.10 × location_score。薪资只展示原始信息，不进入总分。")
    _add_table(doc, ["输出", "对用户的解释", "可核验字段"], [
        ["match_score 与四个分项", "解释为何排在 Top-k，而不是预测录用。", "skill_score、category_score、experience_score、location_score。"],
        ["命中与缺失技能", "显示简历技能与岗位技能的交集及岗位技能缺口。", "matched_skills、missing_skills、岗位标题与描述。"],
        ["岗位追溯信息", "用户可回到原岗位页面人工核验。", "job_id、source_url、crawl_time、data_origin。"],
    ])

    doc.add_heading("五、岗位聚类：K-Means 实现与 K 值选择", level=1)
    doc.add_paragraph("聚类以 job_title、skills_normalized、job_category、broad_category、description_clean 为文本来源。标题和技能重复三次、类别重复两次后进行 TF-IDF 向量化（8,000 特征），再经 TruncatedSVD 压缩到 50 维，由 K-Means 聚类。高权重术语回到原始 TF-IDF 中提取，以保证业务命名可解释。")
    doc.add_paragraph(f"候选 K={manifest.get('candidate_k', [])}。Inertia 随 K 增大而下降，肘部代理为 K={manifest.get('elbow_k', '')}；轮廓系数最高为 K={manifest.get('silhouette_k', '')}（0.1976）。本次以可分性优先，并结合四类业务解释性，最终选择 K={manifest.get('selected_k', '')}。")
    k_rows = [[int(row.k), f"{row.inertia:.2f}", f"{row.silhouette_score:.4f}"] for row in k_metrics.itertuples()]
    _add_table(doc, ["K", "Inertia", "轮廓系数"], k_rows)
    _add_figure(doc, ROOT / "reports/clustering/elbow_plot.png", "图 2  K-Means 肘部图：Inertia 下降趋势用于观察折点，代理建议 K=6。", width=5.7)
    _add_figure(doc, ROOT / "reports/clustering/silhouette_plot.png", "图 3  轮廓系数：候选 K 中 K=4 最高，因此作为最终 K 的主要量化依据。", width=5.7)

    doc.add_page_break()
    doc.add_heading("六、PCA 降维图、业务命名与解读", level=1)
    doc.add_paragraph("二维展示使用同一 SVD 表示再做 PCA 投影。PCA 图用于观察不同聚类的相对分布和重叠，不等价于原始高维空间中的分类边界；本次没有执行 t-SNE，故不对 t-SNE 可视化作任何结论。")
    _add_figure(doc, ROOT / "reports/clustering/cluster_scatter_pca.png", "图 4  K=4 岗位聚类的 PCA 二维投影（颜色为 K-Means 标签）。", width=5.8)
    cluster_rows = []
    for item in summaries:
        titles = "；".join(x["title"] for x in item["top_titles"][:2])
        skills = "、".join(x["skill"] for x in item["top_skills"][:5])
        cluster_rows.append([
            f"{item['cluster_id']}：{item['business_name']}",
            f"{item['job_count']:,}（{item['share'] * 100:.1f}%）",
            item["dominant_broad_category"],
            skills,
            titles,
        ])
    _add_table(doc, ["聚类业务名称", "规模", "主类别", "主要技能", "典型标题"], cluster_rows)
    doc.add_paragraph("业务解读：云平台与 DevOps 工程岗位聚集软件、后端、云与数据工程技能；销售与业务拓展岗位规模最大，聚焦销售、客户与账户管理；企业应用与技术创新岗位是小规模工程细分群；机器学习与人工智能岗位集中 AI 安全、评估与质量保障主题。名称基于高权重词、典型标题和主类别生成，不是官方职业分类。")

    doc.add_heading("七、RAG 检索与 Agent 工具编排", level=1)
    doc.add_paragraph(
        f"正式 RAG 已切换为真实 Embedding 检索：向量库为 {vector_store.get('name', 'FAISS')} {vector_store.get('index_type', 'IndexFlatIP')}，"
        f"Embedding 为 {embedding.get('model', 'BAAI/bge-small-zh-v1.5')}（{embedding.get('dimension', 512)} 维，本地加载）。"
        f"主索引按岗位介绍、岗位职责和任职要求分区建块，Chunk={chunking.get('chunk_size', 1200)}、Overlap={chunking.get('chunk_overlap', 200)}，"
        f"共 {chunking.get('chunk_count', '')} 个 Chunk。测试问题 {question_count} 个，Top-k=3；"
        f"Query Hit@3={_pct(rag_eval.get('query_hit_rate_at_3'))}，Macro Precision@3={_pct(rag_eval.get('macro_precision_at_3'))}，"
        f"Macro MRR@3={_pct(rag_eval.get('macro_mrr_at_3'))}，来源字段完整率={_pct(rag_eval.get('source_trace_coverage'))}。"
        "金标准是可复现的结构化条件，不是人工标注真实 Recall@k；结果均保留 source_url、crawl_time 和 data_origin。"
    )
    doc.add_paragraph(
        f"TF-IDF 基线仍保留在 reports/rag_tfidf_baseline/，对应 {tfidf_eval.get('test_question_count', 10)} 个问题、"
        f"Top-k={tfidf_eval.get('top_k', 3)}，预设条件可验证命中率={tfidf_eval.get('criterion_hit_rate_percent', '')}%。"
        "该基线只用于对照，不冒充 Embedding RAG，也不把 TF-IDF 说成深度学习。"
    )
    doc.add_paragraph(
        f"Agent 真实演示记录于 reports/agent/real_demo_output.json：agent_mode={agent_real.get('agent_mode')}，"
        f"model_call={agent_real.get('model_call')}，protocol={agent_real.get('protocol')}，model={agent_real.get('model')}，"
        f"工具链为 {_tool_chain(agent_real)}。"
        f"离线 fallback 记录于 reports/agent/demo_output.json：agent_mode={agent_fallback.get('agent_mode')}，"
        f"model_call={agent_fallback.get('model_call')}，工具链为 {_tool_chain(agent_fallback)}。"
        "可用工具包括 search_jobs、score_job、match_resume、cluster_summary、retrieve_jobs；"
        "Function Calling schema 与 Prompt 版本已分别保存在 reports/agent/function_schemas.json、docs/prompts/week2_agent_v1.md 和 reports/agent/prompt_versions.md。"
    )

    doc.add_heading("八、结论与局限", level=1)
    doc.add_paragraph(
        "本次调优完成了评分模型的四模型比较、K-Means 的 K 值选择与 PCA 可视化，以及正式 Embedding RAG 与真实模型 Agent 的链路闭环。"
        "评分当前选择 XGBoost；岗位匹配保持可解释的 TF-IDF 基线；聚类当前选择 K=4；RAG 以 FAISS + BGE 为主、TF-IDF 为历史基线；"
        "Agent 以真实 Function Calling 演示为主，并保留本地规则路由 fallback。"
        "局限包括单一公开平台的数据偏向、技能词典覆盖范围、跨语言检索失败题、K-Means 的近似凸簇假设，以及缺少人工相关性与招聘结果标签。"
        "所有结论均限定于当前 12,000 条全球远程岗位数据。"
    )
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            _set_run_font(run, east_asia="STHeiti")
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        _set_run_font(run, east_asia="STHeiti")
    DOCX_OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(DOCX_OUT)


def build_docx_ascii() -> None:
    """Build an ASCII-only companion report for portable LibreOffice rendering."""
    metrics = pd.read_csv(METRICS)
    manifest = _load_json(CLUSTER_MANIFEST, {})
    summaries = _load_json(CLUSTER_SUMMARY, [])
    rag_manifest = _load_json(RAG_MANIFEST, {})
    rag_eval = _load_json(RAG_EVAL, {})
    rag_tests = _load_json(RAG_TESTS, [])
    agent_real = _load_json(AGENT_REAL, {})
    agent_fallback = _load_json(AGENT_FALLBACK, {})
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    styles = doc.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10.5)
    for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        styles[style_name].font.name = "Arial"
        styles[style_name].font.color.rgb = RGBColor(0, 0, 0)
        style_rpr = styles[style_name]._element.get_or_add_rPr()
        style_fonts = style_rpr.find(qn("w:rFonts"))
        if style_fonts is None:
            style_fonts = OxmlElement("w:rFonts")
            style_rpr.append(style_fonts)
        style_fonts.set(qn("w:eastAsia"), "Arial")
    title_style_ppr = styles["Title"]._element.find(qn("w:pPr"))
    if title_style_ppr is not None:
        title_border = title_style_ppr.find(qn("w:pBdr"))
        if title_border is not None:
            title_style_ppr.remove(title_border)
    title = doc.add_paragraph(style="Title")
    _remove_paragraph_borders(title)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("Multi-Model Comparison Report")
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run("Global Remote Job Quality, Matching, Clustering and RAG Prototype\n").bold = True
    subtitle.add_run(f"Week 2 / M2 - {REPORT_DATE}")

    doc.add_heading("Scope", level=1)
    doc.add_paragraph("This report compares job-information quality scoring, resume-to-job matching, job clustering, local retrieval and the Agent workflow. All figures come from the current project outputs and cover global remote jobs.")
    doc.add_heading("Data Base", level=1)
    doc.add_paragraph("The cleaned parquet file contains 12,000 jobs. Each record keeps job_id, source_url, crawl_time and data_origin. A quality score measures information completeness and transparency. A match score ranks jobs for a resume and is not a hiring probability.")
    doc.add_heading("Cross-Model Comparison", level=1)
    metric_text = "; ".join(f"{row.model}: F1 {row.f1:.4f}, AUC {row.roc_auc:.4f}" for row in metrics.itertuples())
    rows = [
        ["Job quality", "Information completeness", "Numeric + categorical + TF-IDF; four classifiers", metric_text, "Complete", "Proxy label"],
        ["Resume matching", "Rank jobs for a resume", "TF-IDF cosine; weights 55/20/15/10", "match_score, components, skills and links", "Complete", "Limited skill lexicon"],
        ["Job clustering", "Discover job groups", f"Weighted TF-IDF + K-Means; K={manifest.get('selected_k','')}", f"{len(summaries)} named groups", "Complete", "Category bias"],
        ["RAG retrieval", "Retrieve traceable jobs", "Local TF-IDF cosine baseline", f"{rag_manifest.get('records','')} records; {len(rag_tests)} test questions", "Prototype", "Not deep embedding"],
        ["Agent workflow", "Route multiple tools", "OpenAI-compatible Function Calling + local fallback", "Tool calls, scores, skills and links", "Real model demo complete", "Fallback remains labeled"],
    ]
    _add_table(doc, ["Module", "Business goal", "Core method", "Output / evaluation", "Status", "Limit"], rows)

    doc.add_heading("Quality Model Results", level=1)
    doc.add_paragraph("The labels are rule-based proxies for job information quality. XGBoost is the current best model on the existing test set with F1=0.9140 and ROC-AUC=0.9662.")
    _add_table(doc, ["Model", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC"], [[row.model, f"{row.accuracy:.4f}", f"{row.precision:.4f}", f"{row.recall:.4f}", f"{row.f1:.4f}", f"{row.roc_auc:.4f}"] for row in metrics.itertuples()])

    doc.add_heading("Resume Matching", level=1)
    doc.add_paragraph("The existing formula is reused: skill_score = 100 * [0.70 * cosine_similarity + 0.30 * matched_skill_count / job_skill_count]. match_score = 0.55 * skill_score + 0.20 * category_score + 0.15 * experience_score + 0.10 * location_score. Salary is display-only.")
    doc.add_paragraph("The demo returns match_score, quality_score, quality_level, matched and missing skills, source URL and a traceable explanation. It is a ranking aid, not an employment probability.")

    doc.add_heading("Job Clustering", level=1)
    doc.add_paragraph(f"Candidate K values are {manifest.get('candidate_k', [])}. The elbow proxy is K={manifest.get('elbow_k','')}; the highest silhouette score is K={manifest.get('silhouette_k','')}; the combined rule selects K={manifest.get('selected_k','')}.")
    cluster_rows = [[x["cluster_id"], f"{x['dominant_broad_category']} group", f"{x['job_count']:,}", x["dominant_broad_category"], ", ".join(s["skill"] for s in x["top_skills"][:5])] for x in summaries]
    _add_table(doc, ["Cluster", "Business label", "Jobs", "Main category", "Top skills"], cluster_rows)
    doc.add_paragraph("The sample is concentrated in Engineering and Data Science. Labels are generated from high-weight terms and categories, then require human spot checks before being treated as a stable occupational taxonomy.")

    doc.add_heading("RAG and Agent", level=1)
    doc.add_paragraph(f"Formal RAG uses FAISS + {rag_manifest.get('embedding', {}).get('model', 'BAAI/bge-small-zh-v1.5')} with {rag_manifest.get('chunking', {}).get('chunk_count', '')} chunks and {rag_eval.get('question_count', len(rag_tests))} test questions. Query Hit@3={_pct(rag_eval.get('query_hit_rate_at_3'))}. Results keep source_url.")
    doc.add_paragraph(f"The Agent real demo uses {agent_real.get('agent_mode')} with model_call={agent_real.get('model_call')} and tool chain {_tool_chain(agent_real)}. Fallback remains {agent_fallback.get('agent_mode')} with model_call={agent_fallback.get('model_call')}. Function Calling schemas and Prompt versions are saved in the project.")

    doc.add_heading("Limitations and Next Steps", level=1)
    doc.add_paragraph("The sample comes from one public platform and is biased toward technical and data roles. TF-IDF retrieval relies on English skill tokens for mixed-language questions. Week 3 should add API integration, system tests, deployment and final defense materials.")
    doc.add_heading("Week 2 Delivery Status", level=1)
    _add_table(doc, ["Task", "Status", "Evidence"], [
        ["Resume matching", "Complete", "Existing formula and JSON demo"],
        ["Job clustering", "Complete", f"K={manifest.get('selected_k','')}; plots, summaries and report"],
        ["Model comparison", "Complete", "Four real model metrics and cross-model analysis"],
        ["RAG retrieval", "Formal RAG complete", "FAISS + BGE, 12-question evaluation"],
        ["Agent", "Real model complete", "Schemas, real demo, fallback and Prompt versions"],
        ["M2 materials", "Complete", "Report and PPT outline"],
    ])
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            _set_run_font(run, "Arial", "Arial")
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        _set_run_font(run, "Arial", "Arial")
    DOCX_OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(DOCX_OUT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Week 2 Markdown, outline and optional DOCX")
    parser.add_argument("--no-docx", action="store_true", help="only write Markdown and PPT outline")
    args = parser.parse_args()
    markdown = build_markdown()
    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.write_text(markdown, encoding="utf-8")
    OUTLINE_OUT.parent.mkdir(parents=True, exist_ok=True)
    OUTLINE_OUT.write_text(build_outline(), encoding="utf-8")
    if not args.no_docx:
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx is required for DOCX output; use --no-docx for text outputs")
        build_docx(markdown)
        print(DOCX_OUT)
    else:
        print("DOCX skipped (--no-docx)")
    print(MD_OUT)
    print(OUTLINE_OUT)


if __name__ == "__main__":
    main()
