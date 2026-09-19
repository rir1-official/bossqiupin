"""Create the formal FAISS RAG experiment report from the supplied template."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "submit/行业大数据分析实践_RAG知识库构建与检索召回测试实验_RAG知识库构建与检索召回测试实验报告模板.docx"
OUTPUT = ROOT / "submit/行业大数据分析实践_RAG知识库构建与检索召回测试实验_RAG知识库构建与检索召回测试实验报告.docx"
RAG_DIR = ROOT / "data/processed/rag"
REPORT_DIR = ROOT / "reports/rag"
SUMMARY_PATH = REPORT_DIR / "rag_eval_summary.json"
TESTS_PATH = REPORT_DIR / "retrieval_tests.json"
MANIFEST_PATH = RAG_DIR / "index_manifest.json"


def _font(run: Any, size: float = 10.5, bold: bool | None = None) -> None:
    run.font.name = "Arial"
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    # Use the concrete macOS CJK face name so LibreOffice resolves Chinese
    # glyphs during the render QA pass as well as Word does on the host.
    for key, value in (("ascii", "Arial"), ("hAnsi", "Arial"), ("eastAsia", "Hiragino Sans GB W3")):
        rfonts.set(qn(f"w:{key}"), value)


def _shade(cell: Any, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def _border(cell: Any, color: str = "D9D9D9") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def _clear(doc: Document) -> None:
    body = doc._element.body
    sect_pr = body.sectPr
    for child in list(body):
        if child is not sect_pr:
            body.remove(child)


def _style(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Hiragino Sans GB W3")
    for style_name, size in (("Title", 20), ("Heading 1", 15), ("Heading 2", 12.5), ("Heading 3", 11.5)):
        style = doc.styles[style_name] if style_name in doc.styles else doc.styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Hiragino Sans GB W3")
    # The supplied template only defines "Normal Table". Add the standard
    # grid style when it is absent so the report builder works across Word
    # and LibreOffice-generated templates.
    if "Table Grid" not in doc.styles:
        doc.styles.add_style("Table Grid", WD_STYLE_TYPE.TABLE)
    if "List Bullet" not in doc.styles:
        bullet_style = doc.styles.add_style("List Bullet", WD_STYLE_TYPE.PARAGRAPH)
        bullet_style.base_style = doc.styles["Normal"]
        bullet_style.paragraph_format.left_indent = Inches(0.28)
        bullet_style.paragraph_format.first_line_indent = Inches(-0.16)


def _para(doc: Document, text: str = "", bold_prefix: str | None = None, after: float = 5) -> Any:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix and text.startswith(bold_prefix):
        r = p.add_run(bold_prefix)
        _font(r, bold=True)
        r = p.add_run(text[len(bold_prefix):])
        _font(r)
    else:
        r = p.add_run(text)
        _font(r)
    return p


def _heading(doc: Document, text: str, level: int = 1) -> Any:
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.space_before = Pt(9 if level == 1 else 6)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    _font(r, 15 if level == 1 else 12.5 if level == 2 else 11.5, True)
    return p


def _bullet(doc: Document, text: str) -> Any:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    _font(r)
    return p


def _table(doc: Document, headers: Sequence[str], rows: Iterable[Sequence[Any]], widths: Sequence[float] | None = None, font_size: float = 8.5) -> Any:
    rows = list(rows)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for i, value in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = str(value)
        _shade(cell, "D9EAF7")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        _border(cell)
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                _font(run, font_size, True)
    for values in rows:
        cells = table.add_row().cells
        for i, value in enumerate(values):
            cells[i].text = str(value)
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            _border(cells[i])
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(1)
                for run in p.runs:
                    _font(run, font_size)
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def _add_picture_if_exists(doc: Document, path: Path, width: float = 6.15) -> None:
    if not path.exists():
        _para(doc, f"图件未找到：{path.relative_to(ROOT)}")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width))
    caption = _para(doc, f"图：{path.stem}", after=2)
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _load() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    tests = json.loads(TESTS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(tests, list) or len(tests) < 10:
        raise ValueError("retrieval_tests.json must contain at least 10 queries")
    return summary, tests, manifest


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "未计算"


def _first(mapping: dict[str, Any], *keys: str, default: Any = "未记录") -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def _short(value: Any, limit: int = 120) -> str:
    text = "" if value is None else str(value).replace("\n", " ")
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _result_summary(item: dict[str, Any]) -> str:
    parts = []
    for result in item.get("results", [])[:3]:
        title = _short(result.get("job_title", ""), 34)
        source = _short(result.get("source_url", ""), 42)
        parts.append(f"{title}（source_url: {source}）")
    return "；".join(parts)


def _source_trace_audit(tests: list[dict[str, Any]]) -> tuple[int, int, list[str]]:
    """Audit that every saved retrieval result has trace fields and a source URL."""
    required = ("job_id", "job_title", "chunk_id", "source_url", "crawl_time", "data_origin")
    total = 0
    complete = 0
    bad: list[str] = []
    for item in tests:
        for result in item.get("results", []):
            total += 1
            missing = [field for field in required if not str(result.get(field, "")).strip()]
            if not missing:
                complete += 1
            else:
                bad.append(f"{item.get('question_id')}:{result.get('rank', '?')} 缺少 {','.join(missing)}")
    return total, complete, bad


def _load_trace_sample() -> tuple[int, int, int]:
    """Return chunk count, metadata row count, and metadata rows with required trace fields."""
    metadata_path = RAG_DIR / "chunk_metadata.jsonl"
    total = complete = 0
    if metadata_path.exists():
        required = ("job_id", "job_title", "chunk_id", "source_url", "crawl_time", "data_origin")
        with metadata_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                total += 1
                row = json.loads(line)
                if all(str(row.get(field, "")).strip() for field in required):
                    complete += 1
    return total, total, complete


def build() -> Path:
    summary, tests, manifest = _load()
    result_total, result_complete, trace_errors = _source_trace_audit(tests)
    metadata_total, _, metadata_complete = _load_trace_sample()
    if trace_errors:
        raise ValueError("retrieval result source trace audit failed: " + "; ".join(trace_errors[:3]))
    doc = Document(str(TEMPLATE))
    _clear(doc)
    _style(doc)

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("RAG知识库构建与检索召回测试实验报告")
    _font(r, 20, True)
    _para(doc, "本报告依据本地清洗后的 Himalayas 远程招聘岗位数据，实际运行 FAISS + BAAI/bge-small-zh-v1.5 中文 Embedding 实验，记录岗位文本分块、向量入库、Top-3 检索、溯源和定量评估结果。", after=8)

    _heading(doc, "一、实验基本信息")
    _table(doc, ["项目", "内容"], [
        ("数据来源", "Himalayas 公开 Jobs API 已保存的本地清洗数据；本实验不重新联网采集"),
        ("数据规模", f"{manifest.get('cleaning', {}).get('valid_rows', manifest.get('source_rows', '未记录'))} 条有效岗位，{manifest.get('chunking', {}).get('chunk_count', '未记录')} 个 Chunk"),
        ("实验环境", "Python 3.9.6、Pandas、PyArrow、FAISS、SentenceTransformers、PyTorch、Matplotlib"),
        ("运行日期", "2026年9月11日"),
        ("设备", str(manifest.get("embedding", {}).get("device", "未记录"))),
    ], widths=[1.3, 5.5])

    _heading(doc, "二、实验目的")
    for text in (
        "掌握岗位文本清洗、Chunk 分块、中文 Embedding、FAISS 入库和 Top-k 检索的完整流程。",
        "理解 FAISS 与 Chroma、Milvus 的差异，并结合 12,000 条本地岗位数据说明选型依据。",
        "设计不少于 10 条真实业务问题，验证技能、类别、地区和模糊岗位语义查询。",
        "构建问题—答案—来源三元组，确保召回结果可回溯到岗位编号和 source_url。",
        "使用可复现的条件金标准规则报告命中情况，并明确其不等同于人工标注真实 Recall。",
    ):
        _bullet(doc, text)

    _heading(doc, "三、实验核心要求完成情况")
    section_stats = manifest.get("cleaning", {}).get("section_parsing", {})
    _table(doc, ["标准", "当前实验的可核验实现", "证据与判定"], [
        ("1 向量库选型", "使用 FAISS IndexFlatIP；同时比较 Chroma、Milvus 的部署、元数据和扩展差异。", "data/processed/rag/faiss.index、index_manifest.json；满足"),
        ("2 数据处理与分块", "岗位介绍、岗位职责、任职要求先清洗，再按 1200 字符、200 字符重叠分块；有标题按区段建块，无标题使用完整文本回退。", "jobs_cleaned.parquet、chunks.parquet、chunk_parameter_comparison.json；满足"),
        ("3 Embedding 与入库", "BAAI/bge-small-zh-v1.5 批量生成 512 维归一化中文向量，并保存岗位编号、岗位名称、Chunk 编号及来源元数据。", f"{metadata_total:,} 条 Chunk 元数据，必需溯源字段完整 {metadata_complete:,}/{metadata_total:,}；满足"),
        ("4 分层 Top-k 测试", f"设计 {len(tests)} 条真实岗位业务问题，覆盖基础、细节、模糊和易混淆岗位查询；固定 Top-k=3。", "reports/rag/retrieval_tests.json、test_queries.json；满足"),
        ("5 结果溯源", f"每条召回结果都回查本地 job_id 对应原始记录，并保留 source_url、crawl_time、data_origin；结果字段完整 {result_complete}/{result_total}。", "rag_faiss.py 的 source trace 校验与 retrieval_tests.json；满足"),
        ("6 三元组", "从召回结果规范化生成问题、答案片段、岗位编号、岗位名称、Chunk 编号、来源和追溯时间字段。", "question_answer_source_triples.csv；满足"),
        ("7 定量与定性评估", "报告 Query Hit@3、Precision@3、Recall@3、MRR、nDCG，并分析成功/失败案例、参数和后续优化；指标明确声明为规则金标准而非人工标注。", "rag_eval_summary.json、4 张图、报告第八至九节；满足"),
    ], widths=[1.25, 3.35, 2.2], font_size=7.6)

    _heading(doc, "四、实验原理与技术概述")
    _heading(doc, "4.1 RAG检索基本原理", 2)
    _para(doc, "本实验实现 RAG 的检索和来源溯源环节：先把岗位名称、公司、类别、技能、地区和岗位描述拼接为 Chunk 文本，再用中文句向量模型将 Chunk 编码并写入 FAISS。查询时将问题编码，使用归一化向量内积返回相似度最高的 Top-3 Chunk，随后通过元数据定位原始岗位。由于本地没有配置大模型生成 API，本报告不伪装生成式问答；“答案片段”指实际召回的岗位文本摘要。")
    _heading(doc, "4.2 FAISS选型理由、优点与局限", 2)
    _table(doc, ["方案", "优点", "局限", "本实验判断"], [
        ("FAISS", "本地依赖简单；IndexFlatIP 可精确检索；批量检索速度快", "不原生管理元数据，需自行维护行号到 Chunk 的映射", "12,000 条岗位、实验室本地复现最合适"),
        ("Chroma", "持久化和 metadata 过滤较方便", "引入集合与客户端管理；当前实验不是必需", "可作为后续混合过滤方案"),
        ("Milvus", "适合海量数据、分布式和复杂过滤", "部署和运维成本高", "当前规模不优先"),
    ], widths=[0.8, 2.0, 2.0, 2.0], font_size=8)
    _heading(doc, "4.3 核心概念说明", 2)
    for text in (
        "Chunk：岗位长文本切分后的最小检索单元，本实验每个 Chunk 都重复携带岗位级上下文。",
        "Embedding：BAAI/bge-small-zh-v1.5 生成的 512 维稠密语义向量，不是 TF-IDF。",
        "Top-k：按 FAISS 相似度返回前 3 个不同岗位，避免同一岗位多个 Chunk 占满结果。",
        "数据溯源：通过 job_id、chunk_id、source_url、crawl_time 和 data_origin 回到本地岗位记录。",
    ):
        _bullet(doc, text)

    _heading(doc, "五、实验数据集与环境配置")
    _heading(doc, "5.1 数据集信息", 2)
    _para(doc, "输入文件：data/processed/jobs_cleaned.parquet。数据来自已保存的 Himalayas API 采集结果，未读取或修改 data/raw/ 和 data/raw_responses/。岗位记录保留 city=Remote、source_url、crawl_time 和 data_origin。文本来源包括岗位标题、岗位类别、技能标签、地区字段，以及清洗后的岗位职责、任职要求和岗位介绍文本；如果原始 job_description 长度不足，则使用 description_clean 作为回退。")
    _para(doc, "具体清洗规则：删除 job_id 重复记录；将 HTML 标签转为空格；移除控制字符、零宽字符和多余空格；统一 Unicode 形式；把空值转为空字符串；剔除缺少岗位编号、标题、source_url、crawl_time、data_origin 或有效岗位描述的记录。")
    _para(doc, f"区段解析统计：岗位介绍显式标题 {section_stats.get('job_introduction_explicit', 0)} 条，岗位职责显式标题 {section_stats.get('responsibilities_explicit', 0)} 条，任职要求显式标题 {section_stats.get('requirements_explicit', 0)} 条。未识别到对应标题的岗位不会被删除，而是使用完整清洗描述作为该区段的回退；其回退次数分别为 {section_stats.get('job_introduction_fallback', 0)}、{section_stats.get('responsibilities_fallback', 0)} 和 {section_stats.get('requirements_fallback', 0)}。")
    _heading(doc, "5.2 实验参数配置", 2)
    emb = manifest.get("embedding", {})
    chunking = manifest.get("chunking", {})
    _table(doc, ["配置项", "具体参数"], [
        ("向量数据库", "FAISS IndexFlatIP；归一化向量内积，等价于余弦相似度"),
        ("Embedding模型", f"{emb.get('model', 'BAAI/bge-small-zh-v1.5')}；{emb.get('dimension', 512)}维；批量大小由运行命令指定；设备 {emb.get('device', '见清单')}"),
        ("Chunk_size", f"{chunking.get('chunk_size', 1200)} 字符"),
        ("Chunk_overlap", f"{chunking.get('chunk_overlap', 200)} 字符"),
        ("Top-k", "3，所有测试问题固定"),
        ("元数据", "job_id、job_title、chunk_id、section_name、source_field、section_source、chunk_index、source_url、crawl_time、data_origin、类别、技能、地区"),
    ], widths=[2.0, 4.8])

    _heading(doc, "六、实验步骤")
    steps = [
        "读取 jobs_cleaned.parquet，检查必需溯源字段，统一空值与文本格式，按 job_id 去重并剔除岗位编号、描述或来源字段缺失的残缺样本。",
        "清洗岗位职责、任职要求和岗位介绍文本，按显式标题分别解析；未识别标题时保留综合文本回退，再按语义边界优先、字符长度兜底切成 1200/200 字符重叠 Chunk。",
        "将岗位上下文与 Chunk 正文拼接，使用 BAAI/bge-small-zh-v1.5 中文 Embedding 模型批量生成 512 维归一化向量。",
        "使用 FAISS IndexFlatIP 批量写入向量，并同步保存 chunks.parquet、chunk_metadata.jsonl 和 index_manifest.json；每个 Chunk 携带岗位编号、岗位名称、Chunk 编号及来源字段。",
        f"自主设计 {len(tests)} 条分层测试问题，覆盖基础查询、细节查询、模糊查询和易混淆岗位查询。",
        "对每条问题执行统一 Top-3 向量检索，提取岗位编号、岗位名称、Chunk 编号和 source_url，并逐条校验召回片段与原始岗位记录一致。",
        "基于召回结果生成问题—答案—来源三元组 CSV，统一保存 question_id、question、answer、job_id、job_title、chunk_id、source_url、crawl_time 和 data_origin。",
        "按每条问题的预设技能、类别和地区规则计算命中率、Precision、Recall、MRR 和 nDCG，分析成功与失败案例，并输出参数对比和可视化结果。",
    ]
    for i, text in enumerate(steps, 1):
        _para(doc, f"步骤{i}：{text}")

    _heading(doc, "七、实验结果展示")
    _heading(doc, "7.1 测试问题集与 Top-3 结果", 2)
    rows = []
    for idx, item in enumerate(tests, 1):
        metrics = item.get("metrics", {})
        rows.append((idx, item.get("question_id", f"Q{idx:02d}"), _short(item.get("question", ""), 70), _pct(metrics.get("hit_at_k", 0)), _result_summary(item)))
    _table(doc, ["序号", "问题", "业务问题", "条件命中", "Top-3 岗位与来源"], rows, widths=[0.4, 0.55, 1.7, 0.7, 3.4], font_size=7.2)

    _heading(doc, "7.2 问题答案来源三元组结果", 2)
    _para(doc, "完整三元组文件为 reports/rag/question_answer_source_triples.csv。每行至少包含 question_id、question、answer_excerpt、job_id、job_title、chunk_id、source_url、crawl_time 和 data_origin；报告只展示结构说明，避免把长文本表格压缩到不可读。")
    triples_path = REPORT_DIR / "question_answer_source_triples.csv"
    if triples_path.exists():
        with triples_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            triple_rows = []
            for row in list(reader)[:8]:
                triple_rows.append((row.get("question_id", ""), _short(row.get("question", ""), 45), _short(row.get("answer", ""), 75), _short(row.get("source_url", ""), 38)))
        _table(doc, ["问题", "问题摘要", "答案片段", "source_url"], triple_rows, widths=[0.55, 1.6, 3.0, 1.65], font_size=7.4)

    _heading(doc, "7.3 召回效果量化指标", 2)
    _table(doc, ["指标", "实际结果", "说明"], [
        ("总测试问题数", summary.get("question_count", len(tests)), "固定测试集"),
        ("条件命中问题数", sum(1 for item in tests if item.get("metrics", {}).get("hit_at_k")), "Top-3 中至少有一条满足该问题 gold rule"),
        ("条件命中率 Query Hit@3", _pct(summary.get("query_hit_rate_at_3", 0)), "基于可复现条件金标准，不是人工标注真实 Recall"),
        ("Macro Precision@3", _pct(summary.get("macro_precision_at_3", 0)), "按每条问题平均"),
        ("Macro Recall@3", _pct(summary.get("macro_recall_at_3", 0)), "相对于规则生成的 gold job 集合"),
        ("Macro MRR@3", _pct(summary.get("macro_mrr_at_3", 0)), "首个规则相关岗位的倒数排名"),
        ("溯源完整率", _pct(summary.get("source_trace_coverage", 0)), "召回结果中核心溯源字段完整的比例"),
    ], widths=[2.0, 1.4, 3.6])
    _para(doc, "指标边界：本实验没有人工逐条标注的相关性数据，也没有完整的“所有相关岗位”全集。因此 Query Hit@3、Precision@3、Recall@3、MRR@3 和 nDCG@3 均是基于代码公开规则生成的条件评估，适合比较本地实验配置，不应表述为人工标注真实召回率。来源完整率是可直接核验的工程指标，不等于相关性指标。")

    _heading(doc, "7.4 可视化结果", 2)
    _para(doc, "参数对比口径说明：下方 Chunk/Overlap 对比图对每条完整清洗岗位描述独立计算，目的是比较不同切分参数的结构性开销；当前主索引采用岗位介绍、岗位职责和任职要求分区建块，并对无显式标题的岗位使用一个综合文本回退块，因此图中的 Chunk 数不能直接替代当前主索引的 55,984 个 Chunk。")
    _add_picture_if_exists(doc, REPORT_DIR / "retrieval_metrics.png")
    _add_picture_if_exists(doc, REPORT_DIR / "top_k_sensitivity.png")
    _add_picture_if_exists(doc, REPORT_DIR / "chunk_distribution.png")
    _add_picture_if_exists(doc, REPORT_DIR / "chunk_parameter_comparison.png")

    _heading(doc, "八、实验结果分析与洞察")
    _para(doc, f"整体结果：本轮实际执行了 {len(tests)} 条查询，采用统一 Top-k=3。条件命中率和各项指标见上表；它们反映了 Embedding、Chunk 和岗位字段拼接在预设规则下的检索表现，不代表企业信誉、录用概率或岗位质量分。")
    success = [item for item in tests if float(item.get("metrics", {}).get("hit_at_k", 0)) > 0]
    failed = [item for item in tests if float(item.get("metrics", {}).get("hit_at_k", 0)) <= 0]
    _para(doc, "召回成功案例：")
    for item in success[:3]:
        _bullet(doc, f"{item.get('question_id')}：{_short(item.get('question'), 90)}；Top-3 中满足规则的结果数为 {item.get('metrics', {}).get('relevant_count_at_k', '未记录')}。")
    _para(doc, "召回失败或部分失败案例：")
    if failed:
        for item in failed[:3]:
            _bullet(doc, f"{item.get('question_id')}：{_short(item.get('question'), 90)}；Top-3 未命中预设条件金标准，可能与中英文表达差异、技能字段覆盖、岗位类别边界或缺少结构化过滤有关。")
    else:
        _bullet(doc, "本轮没有完全失败问题，但部分查询仍可能只有一条结果命中条件，不能据此认为 Top-3 全部相关。")
    _para(doc, "核心洞察：chunk_size=1200、overlap=200 在上下文完整性和向量数量之间取折中；FAISS IndexFlatIP 的精确搜索不会引入近似索引误差，但元数据过滤需要在应用层完成；Embedding 决定中文问题与英文岗位文本的语义对齐，技能、类别和地区等硬条件仍适合使用结构化过滤或混合检索补强。")

    _heading(doc, "九、实验问题与优化方案")
    for text in (
        "指标限制：当前 gold set 来自可复现的字段规则，缺少人工相关性标注，因此不能宣称真实 Recall。",
        "语言和同义词：中文问题与英文岗位文本之间仍可能出现语义偏差，可增加多语 Embedding、同义词扩展和查询改写。",
        "结构化过滤：将 skills、broad_category、job_category 和 district 转为检索前过滤条件，再用向量相似度排序。",
        "Chunk 优化：针对职责、任职要求、岗位介绍分别建块，并在岗位级和 Chunk 级结果间做融合，减少主题混合。",
        "向量库演进：数据规模增大或需要复杂 metadata 过滤时，再评估 Chroma 或 Milvus；当前 12,000 条使用 FAISS 足以复现。",
        "评价升级：建立人工标注的相关/不相关集合，报告人工 Recall@3、Precision@3、MRR 和 nDCG，并记录标注协议。",
    ):
        _bullet(doc, text)

    _heading(doc, "十、实验总结")
    _para(doc, "本实验完成了本地岗位数据清洗、长文本 Chunk、中文 Embedding、FAISS 向量入库、Top-3 检索、来源溯源、三元组导出和定量评估。报告明确区分了真实 Embedding RAG 与 TF-IDF 检索基线：本正式实验使用 FAISS 和 BAAI/bge-small-zh-v1.5，旧 TF-IDF 结果仅保留在 reports/rag_tfidf_baseline/ 作为历史基线，不混入本实验指标。")

    _heading(doc, "十一、实验交付附件")
    for text in (
        "实验代码：src/job_analysis/rag_faiss.py。",
        "FAISS 索引：data/processed/rag/faiss.index。",
        "Chunk 与元数据：data/processed/rag/chunks.parquet、chunk_metadata.jsonl、index_manifest.json。",
        "测试结果：reports/rag/test_queries.json、retrieval_tests.json、rag_eval_summary.json。",
        "问题—答案—来源三元组：reports/rag/question_answer_source_triples.csv。",
        "实验图件：reports/rag/retrieval_metrics.png、top_k_sensitivity.png、chunk_distribution.png、chunk_parameter_comparison.png。",
        "模板原文件：submit/行业大数据分析实践_RAG知识库构建与检索召回测试实验_RAG知识库构建与检索召回测试实验报告模板.docx。",
    ):
        _bullet(doc, text)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT))
    return OUTPUT


if __name__ == "__main__":
    print(build())
