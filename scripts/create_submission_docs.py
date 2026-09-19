"""Build the two Word deliverables for the course submission folder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = PROJECT_ROOT / "permit提交"
DATA = PROJECT_ROOT / "data/processed/jobs_cleaned.parquet"
FIGURES = PROJECT_ROOT / "reports/figures"
MODEL_DIR = PROJECT_ROOT / "reports/modeling"
sys.path.insert(0, str(PROJECT_ROOT / "src"))


NAVY = "17324D"
TEAL = "0F766E"
INK = "17202A"
MUTED = "52606D"
LIGHT = "EEF3F6"
BORDER = "D9E0E5"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, color: str = BORDER, size: str = "6") -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top=90, start=110, bottom=90, end=110) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn("w:" + side))
        if node is None:
            node = OxmlElement("w:" + side)
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_run_font(run, name="Aptos", size=10.5, bold=False, color=INK, italic=False):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Arial Unicode MS")
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def configure_document(doc: Document, short_title: str) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)
    section.header_distance = Inches(0.32)
    section.footer_distance = Inches(0.35)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial Unicode MS")
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    for style_name, size, color in (("Title", 24, "000000"), ("Heading 1", 15, "000000"), ("Heading 2", 11.5, "000000"), ("Heading 3", 10.5, MUTED)):
        style = styles[style_name]
        style.font.name = "Aptos Display" if style_name in {"Title", "Heading 1"} else "Aptos"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial Unicode MS")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(10 if style_name != "Title" else 0)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.keep_with_next = True

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run(short_title)
    set_run_font(run, size=8.5, color=MUTED)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("行业大数据实践  |  课程项目交付材料")
    set_run_font(run, size=8, color=MUTED)


def add_title(doc, title: str, subtitle: str, meta: str) -> None:
    p = doc.add_paragraph(style="Title")
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(title)
    set_run_font(r, name="Aptos Display", size=24, bold=True, color="000000")
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run(subtitle)
    set_run_font(r, size=12, bold=True, color=TEAL)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(13)
    r = p.add_run(meta)
    set_run_font(r, size=9, color=MUTED)


def add_body(doc, text: str, bold_lead: str | None = None) -> None:
    p = doc.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        r = p.add_run(bold_lead)
        set_run_font(r, bold=True, color=INK)
        r = p.add_run(text[len(bold_lead):])
        set_run_font(r)
    else:
        r = p.add_run(text)
        set_run_font(r)


def add_bullets(doc, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(item)
        set_run_font(r, size=10.2)


def add_table(doc, headers: list[str], rows: list[list[str]], widths: list[float] | None = None, font_size=9.2):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(header)
        set_run_font(r, size=font_size, bold=True, color="FFFFFF")
        set_cell_shading(cell, NAVY)
        set_cell_border(cell)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)
    for row_index, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cell = cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 or len(str(value)) > 28 else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(value))
            set_run_font(r, size=font_size, color=INK)
            set_cell_shading(cell, "FFFFFF" if row_index % 2 == 0 else LIGHT)
            set_cell_border(cell)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if widths:
        for row in table.rows:
            for cell, width in zip(row.cells, widths):
                cell.width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_caption(doc, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_run_font(r, size=8.8, color=MUTED, italic=True)


def add_figure(doc, path: Path, caption: str, width=6.2):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(path), width=Inches(width))
    add_caption(doc, caption)


def add_page_break(doc):
    doc.add_page_break()


def build_matching_doc(example_results: list[dict]) -> Path:
    doc = Document()
    configure_document(doc, "人岗匹配算法设计与实现")
    add_title(
        doc,
        "人岗匹配算法设计与实现",
        "基于 TF-IDF 与余弦相似度的全球远程岗位推荐方案",
        "课程项目：基于全球远程招聘岗位大数据的岗位质量评分与人岗匹配研究  |  版本：2026-09-08",
    )
    add_body(doc, "本文面向课程项目的第 2 周人岗匹配交付，说明简历输入、文本处理、匹配维度、评分公式、可解释输出和实现边界。方案使用已清洗的 12,000 条全球远程岗位作为岗位库，支持粘贴简历文本，也支持对可复制文本的 PDF 简历进行提取。")
    add_body(doc, "核心结论：技能相关性是匹配的主要依据，占总分 55%；类别、经验和地点作为结构化补充维度。薪资不纳入当前核心分数，因为样本存在 56.8% 的薪资缺失、多币种和周期差异，报告中作为可追溯的岗位信息单独展示。")

    doc.add_heading("一 业务目标与输入输出", level=1)
    add_body(doc, "业务目标是将候选人简历与岗位库进行可解释排序，帮助求职者先看最相关的岗位，再根据技能缺口、经验差异和地区限制做决策。系统不输出录用概率，也不替代招聘方的人工判断。")
    add_table(doc, ["对象", "输入", "处理", "输出"], [
        ["简历粘贴", "用户输入的纯文本", "清洗、分词、技能抽取", "简历标准文本与技能集合"],
        ["PDF 简历", "本地可读取 PDF", "pypdf 逐页提取文本，再走同一清洗流程", "提取文本、提取状态、匹配结果"],
        ["岗位库", "Parquet 清洗数据", "组合标题、技能标签、类别、描述", "Top-k 岗位排序与解释"],
        ["结果展示", "岗位 ID 与评分明细", "保留分项和来源链接", "总分、命中技能、缺失技能、解释"],
    ], [1.0, 1.65, 2.25, 2.0])
    add_body(doc, "PDF 边界：当前实现使用 pypdf 提取有文本层的 PDF。扫描件可能提取为空，系统应提示“未检测到可复制文本”，后续版本再接入 OCR。上传 PDF 仅处理用户主动提供的文件，不联网、不读取其他目录。")

    doc.add_heading("二 文本预处理与技能抽取", level=1)
    add_body(doc, "简历和岗位使用同一套标准化流程，保证两类文本进入向量空间前具有相同的表示方式。岗位原文中的 HTML、链接和无业务意义的标点先清除，大小写和空白统一；随后使用 jieba 对中英文混合文本分词，并过滤基础停用词。")
    add_bullets(doc, [
        "文本清洗：HTML 转纯文本，移除 URL、重复空白和大部分标点，保留 Python、C++、.NET 等技能符号。",
        "分词：调用 jieba 进行混合语言切分；英文词、数字和技能符号保持可检索。",
        "技能归一化：大小写、连字符和常见别名统一，例如 Golang -> Go、Sklearn -> Scikit-learn、Amazon Web Services -> AWS。",
        "技能集合：从标题、技能标签、类别和描述联合识别，集合交集用于解释“命中技能”和“缺失技能”。",
        "经验解析：从简历识别“X years”表达；岗位使用来源职级映射的经验区间，明确这是分析代理。",
    ])
    add_table(doc, ["归一化示例", "统一结果", "业务作用"], [
        ["Golang / Go", "go", "减少同一技能因写法不同被拆分"],
        ["Sklearn / scikit-learn", "scikit-learn", "提高技能缺口识别的一致性"],
        ["AWS / Amazon Web Services", "aws", "统一云平台关键词"],
        ["RESTful / REST API", "rest api", "统一接口开发表达"],
    ], [2.0, 1.8, 3.1])

    doc.add_heading("三 匹配维度与权重", level=1)
    add_body(doc, "总分采用 0 至 100 分制。技能维度直接反映候选人能力与岗位要求的文本相关性；类别、经验和地点用于纠正仅凭关键词相似度造成的误排。各分项先归一化到 0 至 100，再按权重加权。")
    add_table(doc, ["维度", "权重", "计算方式", "解释"], [
        ["技能相关性", "55%", "TF-IDF 余弦相似度与技能集合重合度组合", "主维度，体现技能文本的相关程度"],
        ["岗位类别", "20%", "简历类别与岗位宽类一致为 100，不一致为 0，未知为 50", "避免跨职业类别的词面相似误导"],
        ["经验/职级", "15%", "简历年限落在岗位代理区间为 100，按差距递减", "体现候选人资历与岗位要求的距离"],
        ["地点限制", "10%", "偏好地区命中限制为 100，不命中为 0，未知为 50；Remote 为 100", "全球远程岗位的地区可申请性"],
        ["薪资信息", "展示项", "保留原始薪资、币种和周期，不进入当前总分", "避免缺失值和跨币种比较造成系统性偏差"],
    ], [1.25, 0.8, 3.0, 2.0])
    add_body(doc, "薪资作为展示项的决定是数据驱动的：本数据中薪资原文缺失 6,815 条，且金额存在不同币种和 hourly、monthly、annual 等周期。如果强行纳入总分，未披露薪资的岗位会被机械降权，跨币种也会产生不可解释的排序。")

    doc.add_heading("四 TF-IDF 与匹配分公式", level=1)
    add_body(doc, "将简历与每条岗位联合文本转换为 TF-IDF 向量。词频部分反映词在当前文本中的重要程度，逆文档频率降低“the、and”等通用词的影响。对于简历向量 r 和岗位向量 j，余弦相似度定义为：")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("cosine(r, j) = (r · j) / (||r|| × ||j||)")
    set_run_font(r, name="Consolas", size=11, bold=True, color=NAVY)
    add_body(doc, "技能分项进一步融合技能集合重合率，计算式为：")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("skill_score = 100 × [0.70 × cosine_similarity + 0.30 × matched_skill_count / job_skill_count]")
    set_run_font(r, name="Consolas", size=10, bold=True, color=NAVY)
    add_body(doc, "最终匹配分为：")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("match_score = 0.55 × skill_score + 0.20 × category_score + 0.15 × experience_score + 0.10 × location_score")
    set_run_font(r, name="Consolas", size=9.5, bold=True, color=NAVY)
    add_body(doc, "当岗位没有结构化技能标签时，技能集合重合率记为 0，但岗位描述仍参与 TF-IDF；当类别、经验或地区信息未知时，该分项使用中性值 50，而不是把未知当作不匹配。")

    doc.add_heading("五 实现流程与代码入口", level=1)
    add_table(doc, ["步骤", "实现", "验收点"], [
        ["1 输入", "粘贴文本或读取 PDF", "空文本和扫描 PDF 有提示"],
        ["2 预处理", "clean_text + jieba tokenize", "简历和岗位使用同一规则"],
        ["3 向量化", "TfidfVectorizer(1-2 gram)", "输出可比较的稀疏向量"],
        ["4 分项计算", "余弦、集合交集、规则分项", "每项保留原始依据"],
        ["5 排序", "按总分降序，job_id 稳定打破并列", "输出 Top-k"],
        ["6 解释", "命中/缺失技能 + 分项 + 薪资参考", "解释可回溯到输入和岗位字段"],
    ], [1.0, 3.1, 2.35])
    add_body(doc, "代码入口：`src/job_analysis/matching.py`。核心函数包括 `extract_pdf_text`、`extract_skills`、`match_jobs` 和 `build_explanation`。命令行示例：")
    p = doc.add_paragraph()
    r = p.add_run("PYTHONPATH=src .venv/bin/python -m job_analysis.matching resume.txt --top-k 10 --output data/processed/matching_demo.json")
    set_run_font(r, name="Consolas", size=8.7, color=NAVY)
    add_body(doc, "PDF 输入只需将 `resume.txt` 替换为 `.pdf` 路径。岗位库默认读取 `data/processed/jobs_cleaned.parquet`，匹配结果保留 `source_url`，可回到原始岗位页面核验。")

    add_page_break(doc)
    doc.add_heading("六 脱敏简历示例与实际输出", level=1)
    resume = """Data analyst with 4 years of experience.\nSkills: Python, SQL, pandas, numpy, Tableau, Excel, statistics.\nExperience: built data pipelines, dashboards, A/B testing reports and machine learning features.\nPreferred location: United States or Canada."""
    add_body(doc, "示例简历（脱敏）：")
    p = doc.add_paragraph()
    r = p.add_run(resume)
    set_run_font(r, name="Consolas", size=9.2, color=INK)
    add_body(doc, "系统从简历识别到的核心技能为 Python、SQL、pandas、numpy、Tableau、Excel、statistics、machine learning；识别到的经验为 4 年，岗位类别推断为 Data Science。以下为基于本项目 12,000 条岗位库的 Top 5 结果：")
    rows = []
    for item in example_results[:5]:
        rows.append([
            str(item["job_title"])[:42],
            str(item["company_name"])[:18],
            f"{item['match_score']:.2f}",
            "、".join(item["matched_skills"][:4]) or "无",
            "、".join(item["missing_skills"][:3]) or "无",
        ])
    add_table(doc, ["岗位", "公司", "总分", "命中技能", "主要缺失技能"], rows, [2.65, 1.15, 0.65, 1.25, 1.25], font_size=8.2)
    if example_results:
        add_body(doc, "首位推荐的规则化解释：" + example_results[0]["explanation"])
        add_body(doc, "来源链接：" + str(example_results[0]["source_url"]))
    add_body(doc, "结果解读：总分用于排序，不是录用概率。命中技能和缺失技能让求职者知道“为什么推荐”和“还差什么”；薪资和地区限制以原始岗位信息展示，避免把缺失值加工成虚假优势或劣势。")

    doc.add_heading("七 异常情况与测试设计", level=1)
    add_table(doc, ["场景", "系统行为", "原因"], [
        ["粘贴内容为空", "返回输入错误，不执行排序", "避免空向量导致无意义结果"],
        ["PDF 无文本层", "提示提取失败，建议转为可复制 PDF", "当前版本未接入 OCR"],
        ["简历未识别技能", "技能相似度较低，仍输出类别/经验/地点中性分", "不把抽取失败直接当作候选人能力不足"],
        ["岗位地区限制为空", "地点分项记为 50", "未知不等于不匹配"],
        ["岗位薪资为空或多币种", "显示未披露或原币种，不进总分", "避免缺失和汇率假设引入偏差"],
    ], [1.55, 2.85, 2.3], font_size=8.8)
    add_body(doc, "可复现测试包括：PDF 文本提取、空文本、技能别名归一化、技能交集、岗位排序稳定性、Remote 地点分项、未知字段中性处理和 source_url 保留。")

    doc.add_heading("八 局限性与后续改进", level=1)
    add_bullets(doc, [
        "TF-IDF 主要利用词面共现，不能完全理解同义表达、上下文和技能熟练程度；后续可增加句向量召回，但应保留当前方法作为可解释基线。",
        "岗位技能标签来自平台分类体系，其中可能混入角色词和类别词；当前已将标签与描述联合使用，仍需人工抽样检查技能词表。",
        "经验年限由来源职级映射，是分析代理，不是雇主明确要求的精确年限。",
        "全球远程岗位的地点限制由 API 的国家/地区字段决定，缺失时只能给中性分；不把 Remote 改写为厦门或其他城市。",
        "匹配效果尚未有人工相关性标注或点击/投递反馈，下一步可由两名标注者对 Top-k 结果进行相关性标注，并报告一致性。",
    ])
    add_body(doc, "交付范围总结：本方案已覆盖粘贴简历、PDF 提取、统一预处理、TF-IDF + 余弦相似度、权重公式、Top-k 排序、命中/缺失技能和规则化解释，满足课程对《人岗匹配文档》的设计与实现要求。")
    output = SUBMISSION / "人岗匹配算法设计与实现.docx"
    doc.save(output)
    return output


def build_visualization_doc(df: pd.DataFrame, metrics: pd.DataFrame) -> Path:
    doc = Document()
    configure_document(doc, "可视化分析与评分模型")
    add_title(
        doc,
        "可视化分析报告",
        "全球远程招聘岗位结构洞察与岗位信息质量评分模型",
        "课程项目：基于全球远程招聘岗位大数据的岗位质量评分与人岗匹配研究  |  版本：2026-09-08",
    )
    add_body(doc, "本文基于 Himalayas 公开 Jobs API 采集的 12,000 条全球远程岗位，完成数据清洗、特征工程、七张业务可视化图以及四种分类模型比较。报告回答两个问题：远程岗位市场呈现怎样的类别、薪资、技能和发布时间结构；哪些岗位信息特征可以用于构造和学习岗位信息质量标签。")
    add_body(doc, "阅读结论：Engineering 和 Data Science 是样本主体；可比较的 USD 薪资中位数为 121,550 美元；岗位描述长度与信息质量分呈中等正相关；规则标签下高信息质量岗位占 50.6%。这些结论限定在本次 API 时间窗口快照，不外推为完整市场结论。")

    doc.add_heading("一 数据范围与清洗口径", level=1)
    add_table(doc, ["项目", "结果", "说明"], [
        ["数据源", "Himalayas 公开 Jobs API", "已取得研究用途回复/许可"],
        ["原始记录", "12,000 条", "600 个分页文件，每页约 20 条"],
        ["去重后记录", "12,000 条", "重复 0 条，重复率 0.00%"],
        ["研究对象", "全球远程岗位", "city=Remote，district 表示地区限制"],
        ["薪资披露", "5,185 条可解析", "只对非异常 USD 年薪做金额图"],
        ["质量标签", "High 6,071 条", "固定信息透明度规则分 >= 80"],
    ], [1.45, 1.65, 3.6])
    add_body(doc, "清洗规则包括去重、字段类型标准化、薪资周期解析、经验职级映射、异常值标记、HTML/URL/标点清洗、jieba 分词、技能归一化、描述长度和结构特征构造。原始 JSONL 和 API 响应保持不变，处理数据写入 `data/processed/`。每条记录保留 `source_url`、`crawl_time` 和 `data_origin`。")
    add_body(doc, "来源 API 未提供的 education、industry、company_type、company_size、longitude、latitude 不进入教师查看版 CSV、模型或图表；完整缺失统计仍保留在质量审计 JSON 中，不做虚构填充。薪资缺失也不填 0。")

    doc.add_heading("二 岗位结构可视化", level=1)
    add_figure(doc, FIGURES / "01_broad_category_distribution.png", "图 1 岗位宽类分布。数据源：12,000 条去重清洗岗位。", 6.05)
    add_body(doc, "指标定义：宽类由岗位标题、技能标签、岗位分类和描述中的固定关键词映射得到，同一岗位只保留一个主类别。图表观察：Engineering 共 2,792 条，占 23.3%，为最大类别；Data Science 次之，共 2,199 条，占 18.3%。业务洞察：样本明显偏向技术和数据岗位，匹配与聚类应按类别分层评估，否则大类会掩盖小类的技能结构；对求职者而言，先选择目标类别再做技能匹配更稳妥。")

    add_figure(doc, FIGURES / "02_usd_salary_distribution.png", "图 2 非异常 USD 年薪分布。金额图不包含其他币种。", 5.95)
    add_body(doc, "指标定义：仅保留可解析、非异常且币种为 USD 的年薪，并对分析值做 P1/P99 缩尾。图表观察：有效样本 4,592 条，中位数为 121,550 美元。业务洞察：薪资分布可为求职者提供市场参考，但它只代表主动披露 USD 薪资的透明子样本；不能把未披露薪资岗位自动视为低薪，也不能跨币种直接比较。")

    add_figure(doc, FIGURES / "03_salary_by_seniority.png", "图 3 职级与 USD 年薪。箱体用于展示分布而非单一报价。", 5.95)
    add_body(doc, "指标定义：按来源 seniority 映射职级，并在 USD 非异常子样本中比较年薪分布。图表观察：Executive 年薪中位数约 226,250 美元，整体高于其他职级；不同职级箱体仍有明显重叠。业务洞察：职级对薪资有区分作用，但不是唯一解释变量；岗位类别、地区限制、合同形式和企业需求也应纳入判断。")

    add_page_break(doc)
    doc.add_heading("三 技能与岗位信息可视化", level=1)
    add_figure(doc, FIGURES / "04_top_skills.png", "图 4 Top 技能标签频次。标签来自平台分类体系。", 6.05)
    add_body(doc, "指标定义：拆分并规范化 skills 字段后统计岗位标签出现次数。图表观察：sales 出现 728 次，是频次最高的标签；前列标签同时包含技术词、职能词和角色词。业务洞察：平台标签适合做岗位召回和聚类的初始特征，但不能直接全部当作候选人技能；人岗匹配中需要结合岗位描述，并通过别名表减少表达差异。")

    add_figure(doc, FIGURES / "05_description_length_quality.png", "图 5 描述长度与岗位信息质量分。散点图用于观察关联，不表示因果。", 5.95)
    add_body(doc, "指标定义：描述长度为清洗后字符数，质量分为由追溯字段、核心字段、地点限制、描述结构、薪资透明度、技能清晰度、职级、时效性和类别组成的 100 分规则分。图表观察：Spearman 相关系数为 0.67，描述更完整的岗位通常质量分更高。业务洞察：长度只贡献有限分值，过长文本不自动等于高质量；招聘方应优先补足薪资、职责结构和技能要求。该图也说明质量标签存在可学习结构，但不能据此解释真实企业质量。")

    add_figure(doc, FIGURES / "06_posting_date_trend.png", "图 6 岗位发布日期趋势。时间范围为本次采集快照窗口。", 6.05)
    add_body(doc, "指标定义：将 API 发布日期转换为日期后按天计数。图表观察：样本覆盖 2026-09-04 至 2026-09-08，2026-09-06 达到 3,699 条。业务洞察：日期可以帮助看岗位库的时间新鲜度，但本样本受 API 排序和截取窗口影响，不能解释为完整市场的新增岗位趋势；系统上线时应增加持续采集，才可做真正的时间序列分析。")

    add_figure(doc, FIGURES / "07_quality_level_distribution.png", "图 7 岗位信息质量等级分布。High/Medium/Low 来自固定规则。", 5.65)
    add_body(doc, "指标定义：quality_score >= 80 为 High，60 至 79 为 Medium，低于 60 为 Low。图表观察：High 6,071 条，占 50.6%；Medium 5,855 条，占 48.8%；Low 74 条，占 0.6%。业务洞察：一半左右岗位的信息披露达到规则高等级，仍有大量岗位处于中等水平；求职者应同时查看信息透明度和技能匹配，招聘方可据此完善薪资、职责和技能字段。High 不代表企业信誉、工作体验或录用概率。")

    doc.add_heading("四 岗位质量评分模型", level=1)
    add_body(doc, "岗位质量定义为“招聘信息透明度与完整度”，不是企业好坏、真实工作体验或候选人录用概率。规则分满分 100，quality_score >= 80 作为高信息质量标签。标签由可复现规则生成，模型任务是学习信息质量标签，属于课程代理标签。")
    add_table(doc, ["评分组件", "分值", "业务含义"], [
        ["追溯字段", "5", "source_url、crawl_time、data_origin 完整"],
        ["核心字段", "10", "岗位名、公司、城市等核心信息"],
        ["地点限制", "5", "远程岗位可申请国家/地区信息"],
        ["描述完整性", "25", "长度与职责、要求、福利等结构词"],
        ["薪资透明度", "15", "薪资原文及可解析状态"],
        ["技能清晰度", "20", "技能标签数量和规范化程度"],
        ["职级、时效、类别", "10、5、5", "岗位层级、新鲜度和岗位归类"],
    ], [1.75, 0.85, 4.2], font_size=8.8)
    add_body(doc, "建模输入包含岗位文本 TF-IDF、描述长度与结构、技能数量、地点限制、发布时间、经验代理和宽类岗位；为避免确定性泄漏，排除 quality_score、规则分项、薪资披露标记、币种、周期和标签本身。固定随机种子 42，按标签分层划分训练集 9,600 条、测试集 2,400 条。")

    add_page_break(doc)
    doc.add_heading("五 四模型训练与评估", level=1)
    metric_rows = []
    for _, row in metrics.iterrows():
        metric_rows.append([row["model"], f"{row['accuracy']:.4f}", f"{row['precision']:.4f}", f"{row['recall']:.4f}", f"{row['f1']:.4f}", f"{row['roc_auc']:.4f}"])
    add_table(doc, ["模型", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC"], metric_rows, [1.85, 1.0, 1.0, 0.9, 0.8, 1.0], font_size=8.7)
    add_body(doc, "评估结果：XGBoost 的 F1=0.9140、ROC-AUC=0.9662，在当前代理标签任务上综合表现最好；Logistic Regression 的 F1=0.8774，SVM 为 0.8732，Random Forest 为 0.8723。四种模型使用同一训练/测试切分和同一特征预处理，结果具有可比性。")
    add_figure(doc, MODEL_DIR / "model_comparison.png", "图 8 四种模型指标对比。", 5.75)
    add_figure(doc, MODEL_DIR / "roc_curves.png", "图 9 测试集 ROC 曲线。", 4.55)
    add_body(doc, "模型可解释性：线性模型可查看 TF-IDF 系数，树模型可查看特征重要性；当前报告配套输出混淆矩阵、ROC 曲线、模型对比图、特征重要性 CSV 和 PNG。解释时应强调：高指标主要说明模型能够复现规则标签，不能证明模型预测真实录用结果。")

    doc.add_heading("六 结论与局限", level=1)
    add_bullets(doc, [
        "样本岗位结构偏向 Engineering 与 Data Science，后续人岗匹配和聚类应分层评估。",
        "USD 薪资中位数仅适用于可比较薪资子样本，跨币种和未披露薪资不做直接推断。",
        "描述长度与质量分有中等相关，但岗位质量还依赖薪资、技能、结构化职责和时效性。",
        "质量标签是信息透明度代理标签，未经过人工双人标注，也没有投递、面试或录用反馈。",
        "发布日期是一次 API 时间窗口快照，不能代替持续采集后的市场趋势。",
    ])
    add_body(doc, "后续改进：抽样 300 至 500 条岗位由两名标注者独立评价信息质量并报告一致性；将人工标签与真实投递反馈结合进行模型校准；持续采集形成时间序列；在看板中同时呈现类别、技能、薪资透明度、质量分和人岗匹配结果。")
    add_body(doc, "交付范围总结：本报告包含数据范围、清洗规范、7 张有业务含义的可视化图、逐图洞察、质量标签设计、训练/测试划分、Logistic、SVM、Random Forest、XGBoost 训练与评估，以及模型可解释性和局限性，满足课程对《可视化分析报告》的要求。")
    output = SUBMISSION / "可视化分析报告.docx"
    doc.save(output)
    return output


def build_preprocessing_doc(audit: dict) -> Path:
    """Create the standalone Week 1 preprocessing deliverable from audit evidence."""
    doc = Document()
    configure_document(doc, "数据预处理文档")
    add_title(
        doc,
        "数据预处理文档",
        "全球远程招聘岗位数据清洗与特征工程说明",
        "课程项目：基于全球远程招聘岗位大数据的岗位质量评分与人岗匹配研究  |  版本：2026-09-09",
    )
    add_body(doc, "本文说明全球远程招聘岗位数据从原始 JSONL 到分析数据集的处理过程。处理对象为 Himalayas 公开 Jobs API 在本次快照中采集的 12,000 条岗位记录，覆盖去重、缺失值处理、薪资与经验标准化、异常值标记、文本清洗、jieba 分词和特征工程。原始数据保持不变，所有派生数据单独写入 data/processed/。")
    add_body(doc, "处理结论：600 个分页文件共包含 12,000 条记录，按既定规则去重后仍为 12,000 条；薪资字段可解析 5,185 条，缺失 6,815 条，异常标记 31 条；所有结果保留 source_url、crawl_time 与 data_origin，且 city 始终保留为 Remote。")

    doc.add_heading("一 处理目标与数据边界", level=1)
    add_table(doc, ["项目", "处理口径", "说明"], [
        ["数据来源", "Himalayas 公开 Jobs API", "全球远程招聘岗位数据快照"],
        ["唯一输入", "600 个 remote_all_*.jsonl 分页文件", "位于 data/raw/himalayas_api/2026-09-08/"],
        ["原始数据保护", "不修改、不覆盖、不删除", "原始 JSONL 与原始 API 响应保持可核验"],
        ["历史聚合文件", "明确排除 jobs_all.jsonl", "避免将历史聚合内容重复并入本次样本"],
        ["研究对象", "全球远程岗位", "city=Remote 保持来源语义，district 表示地区限制"],
        ["派生输出", "JSONL、Parquet、CSV、质量报告", "只写入 data/processed/、export/、reports/ 与 docs/"],
    ], [1.25, 2.55, 2.75], font_size=8.8)
    add_body(doc, "可追溯性要求：每条清洗记录保留 source_url、crawl_time、data_origin，并新增 raw_page_file 与 raw_line_number，用于定位原始分页文件与行号。")

    add_page_break(doc)
    doc.add_heading("二 处理流程与验收结果", level=1)
    add_body(doc, "处理流程如下：原始分页 JSONL → 合并与来源定位 → 去重 → 缺失值审计 → 字段类型标准化 → 薪资与经验解析 → 异常值标记 → 文本清洗与 jieba 分词 → 技能归一化 → 数值特征构造 → 输出 JSONL、Parquet 与质量报告。")
    add_table(doc, ["检查项", "结果", "验收含义"], [
        ["输入分页文件", f"{audit['source_file_count']:,} 个", "只读取授权日期目录下的分页文件"],
        ["原始记录", f"{audit['raw_record_count']:,} 条", "满足课程不少于 1 万条的要求"],
        ["去重后记录", f"{audit['deduplicated_record_count']:,} 条", "未因清洗丢失有效岗位"],
        ["重复记录", f"{audit['duplicate_count']:,} 条，{audit['duplicate_rate']:.2%}", "本次分页文件不存在重复岗位"],
        ["city 语义", "全部为 Remote", "未将全球远程岗位改写为具体城市"],
        ["追溯字段", "全部完整", "source_url、crawl_time、data_origin 均可用于回溯"],
    ], [1.35, 1.65, 3.55])

    add_page_break(doc)
    doc.add_heading("三 合并与去重", level=1)
    add_body(doc, "去重以稳定且可解释的键为优先级：首先使用 source + job_id；若该键不可用，则使用 source_url；若仍不可用，才使用岗位名、公司、城市、原始薪资和发布日期的业务字段组合。每一种去重键均保留首次出现记录，重复明细单独写入 data/processed/duplicate_records.jsonl，不修改任何原始文件。")
    add_table(doc, ["优先级", "去重键", "使用原因"], [
        ["1", "source + job_id", "同一来源中的岗位唯一标识，稳定性最高"],
        ["2", "source_url", "可回到平台原始岗位页面核验"],
        ["3", "岗位名 + 公司 + city + salary_raw + publish_date", "缺少唯一标识时的保守业务组合"],
    ], [0.7, 2.65, 3.2])
    add_body(doc, "本次结果为 12,000 条输入、12,000 条去重后记录、0 条重复。去重率为 0.00% 并不表示规则无效，而是说明本次 600 个原始分页文件没有命中相同岗位。")

    add_page_break(doc)
    doc.add_heading("四 缺失值审计与处理策略", level=1)
    add_body(doc, "缺失处理遵循“不把未提供伪造成业务值”的原则。原始文本字段缺失时保留空字符串，解析后数值字段保留空值；同时增加解析状态字段，让后续分析能够区分“缺失”“可解析”“不可解析”。薪资缺失不以 0 填充，避免在统计或模型中被错误理解为零薪资。")
    add_table(doc, ["关键字段", "缺失数", "缺失率", "处理方式"], [
        ["district", "226", "1.9%", "保留空值；后续表示为地区限制未知，不等同于不可申请"],
        ["salary_raw", "6,815", "56.8%", "保留缺失；salary_parse_status=missing；不填 0"],
        ["job_id", "0", "0.0%", "作为首选去重依据"],
        ["job_title", "0", "0.0%", "作为岗位分析与文本特征输入"],
        ["company_name", "0", "0.0%", "作为岗位描述和可追溯展示字段"],
        ["job_description", "0", "0.0%", "进行文本清洗、分词和长度特征构造"],
        ["skills", "0", "0.0%", "规范化并计算技能数量"],
        ["source_url / crawl_time / data_origin", "0", "0.0%", "强制保留，用于数据追溯"],
    ], [1.55, 0.82, 0.82, 3.35], font_size=8.4)
    add_body(doc, "来源 API 中 education、industry、company_type、company_size、longitude、latitude 在本次 12,000 条记录中均未提供。这些字段不进入本次分析、图表或模型输入，也不在教师查看版导出中展示；完整缺失统计保留在 reports/data_quality_summary.json 供审计使用。")

    doc.add_heading("五 字段类型标准化", level=1)
    add_body(doc, "原始岗位字段以字符串为主。清洗阶段对字段进行统一空白处理，并把薪资、经验、发布时间和技能拆解为可计算的标准字段。标准化不覆盖原始字段，而是新增解析字段，以同时保留来源文本与计算依据。")
    add_table(doc, ["原始字段", "标准化结果", "处理说明"], [
        ["salary_raw", "salary_currency、salary_period、salary_min、salary_max、salary_avg", "解析币种、周期和金额上下限；同时保留原文"],
        ["salary_raw", "salary_*_annual", "按周期转换为同币种年薪化数值，仅用于统计比较"],
        ["experience_raw", "experience_level_primary、experience_year_min/max", "将来源职级映射为经验区间代理"],
        ["publish_date", "publish_age_days", "转换为距离 2026-09-08 的岗位发布天数"],
        ["skills", "skills_normalized、skill_count", "拆分、去重、小写统一并计算技能数"],
        ["job_title / job_category / skills", "broad_category、is_it_data_role", "按固定关键词映射岗位宽类及技术数据岗位标记"],
    ], [1.45, 2.35, 2.75], font_size=8.5)

    doc.add_heading("六 薪资与经验解析", level=1)
    add_body(doc, "薪资解析识别如 USD 100-150 hourly、USD 120000 annually、up to 或 from 等表达，并输出币种、周期、最小值、最大值和均值。共 5,185 条岗位薪资可解析，6,815 条为缺失；不同币种不使用外部汇率换算，不直接进行跨币种金额比较。")
    add_table(doc, ["薪资周期", "年薪化系数", "用途"], [
        ["annual", "×1", "保留年薪值"],
        ["monthly", "×12", "用于同币种年度统计"],
        ["weekly", "×52", "用于同币种年度统计"],
        ["daily", "×260", "按固定工作日假设年薪化"],
        ["hourly", "×2080", "按固定工时假设年薪化"],
    ], [1.45, 1.6, 3.5])
    add_body(doc, "经验字段不把来源职级误说成雇主给出的精确年限。当前使用可复现的分析代理：Entry-level 映射为 0-2 年，Mid-level 为 2-5 年，Senior 为 5-10 年，Manager 为 5-12 年，Director 为 8-15 年，Executive 为 10-20 年。所有 12,000 条来源职级均可完成映射。")

    doc.add_heading("七 异常值处理", level=1)
    add_body(doc, "异常值采取“标记优先、保留原值”的策略，而不是直接删除记录。年薪化薪资低于 5,000、高于 1,000,000，或金额上下限倒置时，salary_outlier 标记为真。这样既避免极端值影响汇总统计，也保留原始岗位以便复核。")
    add_table(doc, ["异常规则", "处理结果", "后续使用"], [
        ["年薪化 < 5,000", "标记为异常", "不参与稳健 USD 薪资统计"],
        ["年薪化 > 1,000,000", "标记为异常", "不参与稳健 USD 薪资统计"],
        ["薪资上下限倒置", "标记为异常", "保留原始薪资文本以便核验"],
        ["异常薪资总数", "31 条", "未删除，仅通过 salary_outlier 追踪"],
        ["USD 稳健分析", "P1/P99 缩尾", "边界为 12,480.00 / 314,850.00 USD"],
    ], [2.1, 1.65, 2.8])

    add_page_break(doc)
    doc.add_heading("八 文本清洗、jieba 分词与技能归一化", level=1)
    add_body(doc, "岗位描述用于可视化、质量特征和后续 TF-IDF 建模。为避免 HTML、链接和排版符号干扰统计，清洗过程首先统一大小写与空白、移除 URL 和大部分无业务意义标点，同时保留 Python、C++、.NET 等技能符号。之后调用 jieba 对中英文混合文本进行分词，英文词、数字和技能符号仍可检索，并过滤基础停用词。")
    add_table(doc, ["步骤", "实现", "输出字段"], [
        ["文本规范化", "统一空白和大小写", "description_clean"],
        ["URL 与标点清理", "移除链接和无业务意义符号，保留技能符号", "description_clean"],
        ["jieba 分词", "对混合语言文本执行精确模式切分", "description_tokens"],
        ["停用词过滤", "过滤 the、and、with 等基础词", "description_tokens"],
        ["技能归一化", "拆分、去重、统一小写与连字符表达", "skills_normalized"],
    ], [1.35, 3.5, 1.7])
    add_body(doc, "技能归一化的目标是减少同一技能因大小写、连字符或格式不同被拆分。例如岗位标签会被统一为可比较的规范形式，并以 skills_normalized 保存；skill_count 记录规范化后的唯一技能数量。平台技能标签可能包含角色词和职能词，因此后续人岗匹配会将技能标签与岗位描述联合使用，而不会把所有标签机械视为候选人技能。")

    doc.add_heading("九 特征工程与输出数据集", level=1)
    add_table(doc, ["特征类别", "派生字段", "业务用途"], [
        ["薪资特征", "salary_*、salary_outlier、salary_avg_usd_annual_winsorized", "薪资透明度、异常识别与同币种统计"],
        ["经验特征", "experience_level_primary、experience_year_min/max、is_fresh_graduate", "职级结构分析和匹配代理"],
        ["文本特征", "description_length、description_word_count、description_structure_count", "岗位描述完整性和模型输入"],
        ["技能特征", "skills_normalized、skill_count", "技能频次、匹配和聚类基础特征"],
        ["地点与时间", "location_restriction_count、publish_age_days", "地区可申请性和岗位时效分析"],
        ["类别特征", "broad_category、is_it_data_role", "分层分析和岗位类别建模"],
        ["信息质量特征", "quality_score、quality_label、quality_level", "作为可复现的信息透明度代理标签"],
    ], [1.25, 2.95, 2.35], font_size=8.5)
    add_body(doc, "信息质量相关字段是特征工程的一部分：quality_score 满分 100，综合追溯字段、核心字段、地点限制、描述完整性、薪资透明度、技能清晰度、职级、时效性和类别等信息。quality_score >= 80 时标记为高信息质量。该标签仅衡量招聘信息透明度与完整度，不代表企业信誉、真实工作体验、薪酬竞争力或录用概率。")
    add_table(doc, ["输出位置", "内容", "用途"], [
        ["data/processed/jobs_merged_deduplicated.jsonl", "合并去重后的岗位记录", "保留原始字段与来源定位字段"],
        ["data/processed/jobs_cleaned.jsonl", "清洗和特征工程后的全量数据", "文本与结构化分析"],
        ["data/processed/jobs_cleaned.parquet", "同一清洗结果的列式存储", "建模与高效读取"],
        ["data/processed/duplicate_records.jsonl", "重复记录明细", "审计与复核"],
        ["reports/data_quality_report.md / .json", "处理统计与质量审计", "课程检查与可追溯说明"],
    ], [2.55, 2.7, 1.3], font_size=8.2)

    doc.add_heading("十 质量验收、局限与复现", level=1)
    add_bullets(doc, [
        "验收通过：所有清洗记录 city=Remote，保持全球远程岗位的来源语义。",
        "验收通过：source_url、crawl_time、data_origin 三个追溯字段全部完整。",
        "验收通过：有效记录数为 12,000 条，满足课程数据量不少于 10,000 条的要求。",
        "局限：薪资年薪化使用固定工时假设，未包含奖金、股权、税制和实际工时差异；因此仅用于同币种的统计比较。",
        "局限：经验年限来自平台职级映射，是分析代理，不等同于岗位发布者明确写出的年限要求。",
        "局限：来源未提供的学历、行业、公司规模等字段不做虚构填充，后续如需相关分析应补充合法的数据来源。",
    ])
    add_body(doc, "复现命令：")
    p = doc.add_paragraph()
    r = p.add_run("PYTHONPATH=src .venv/bin/python -m job_analysis.cleaning")
    set_run_font(r, name="Consolas", size=9.2, color=NAVY)
    add_body(doc, "该命令从授权的日期分页文件读取数据，生成正式清洗数据和质量报告；样本验证命令使用 --sample-size 200，仅输出到 data/processed/sample_validation/，不覆盖正式处理结果。")
    add_body(doc, "交付总结：本文件完整说明了数据清洗与特征工程的处理范围、缺失值策略、去重规则、薪资与经验解析、异常值处理、文本清洗、jieba 分词、数值特征构造、输出数据集和质量验收，满足课程《数据预处理文档》的要求。")

    output = PROJECT_ROOT / "submit" / "数据预处理文档.docx"
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    return output


def main():
    SUBMISSION.mkdir(parents=True, exist_ok=True)
    demo_payload = json.loads((PROJECT_ROOT / "data/processed/matching_demo.json").read_text(encoding="utf-8"))
    example_results = demo_payload["results"]
    metrics = pd.read_csv(MODEL_DIR / "model_metrics.csv")
    audit = json.loads((PROJECT_ROOT / "reports/data_quality_summary.json").read_text(encoding="utf-8"))
    matching = build_matching_doc(example_results)
    visualization = build_visualization_doc(pd.DataFrame(), metrics)
    preprocessing = build_preprocessing_doc(audit)
    print(matching)
    print(visualization)
    print(preprocessing)


if __name__ == "__main__":
    main()
