import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "/Users/kozenki/Documents/ChatGPT/行业大数据实践";
const SKILL_DIR =
  "/Users/kozenki/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const TMP_DIR = path.join(workspaceDir, ".ppt_build", "week2");
const FINAL_PPTX = path.join(workspaceDir, "submit", "Week2汇报_可读版.pptx");
const RUNTIME_PYTHON =
  "/Users/kozenki/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
const FONT_FAMILY = "Hiragino Sans GB";
const W = 1280;
const H = 720;

const colors = {
  navy: "#123A63",
  navyDeep: "#0B2F52",
  blue: "#1867B2",
  teal: "#178E83",
  orange: "#D9822B",
  red: "#C94C4C",
  ink: "#1F2E44",
  muted: "#66788D",
  line: "#D6E2F0",
  surface: "#FFFFFF",
  softBlue: "#EAF3FB",
  softTeal: "#E8F7F5",
  softOrange: "#FFF3E4",
  softRed: "#FCECEC",
  page: "#F2F6FA",
  green: "#238B68",
};

const { finalizePresentation } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href
);

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const ppt = Presentation.create({ slideSize: { width: W, height: H } });
ppt.theme.colorScheme = {
  name: "Week 2 Report",
  themeColors: {
    accent1: colors.blue,
    accent2: colors.teal,
    accent3: colors.orange,
    accent4: colors.red,
    accent5: colors.navy,
    accent6: colors.green,
    bg1: colors.page,
    bg2: colors.surface,
    tx1: colors.ink,
    tx2: colors.muted,
    dk1: colors.navyDeep,
    dk2: colors.navy,
    lt1: colors.surface,
    lt2: colors.line,
    hlink: colors.blue,
    folHlink: colors.teal,
  },
};

function addText(slide, text, options) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: {
      left: options.left,
      top: options.top,
      width: options.width,
      height: options.height,
    },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: FONT_FAMILY,
    fontSize: options.size ?? 18,
    bold: options.bold ?? false,
    color: options.color ?? colors.ink,
    alignment: options.align ?? "left",
    verticalAlignment: options.valign ?? "top",
    autoFit: "shrinkText",
    wrap: "square",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return shape;
}

function addBox(slide, options) {
  const geometry = options.geometry ?? "roundRect";
  const shapeOptions = {
    geometry,
    name: options.name,
    position: {
      left: options.left,
      top: options.top,
      width: options.width,
      height: options.height,
    },
    fill: options.fill ?? colors.surface,
    line: options.line ?? { style: "solid", fill: colors.line, width: 1 },
    shadow: options.shadow ?? "shadow-none",
  };
  if (geometry === "rect" || geometry === "textbox" || geometry === "roundRect") {
    shapeOptions.borderRadius = options.radius ?? 8;
  }
  return slide.shapes.add(shapeOptions);
}

function addLine(slide, left, top, width, color = colors.line, thickness = 1) {
  return slide.shapes.add({
    geometry: "line",
    position: { left, top, width, height: 0 },
    fill: "none",
    line: { style: "solid", fill: color, width: thickness },
  });
}

function addPageFrame(slide, pageNumber, title, subtitle = "") {
  slide.background.fill = colors.page;
  addBox(slide, {
    geometry: "rect",
    left: 0,
    top: 0,
    width: W,
    height: 92,
    fill: colors.navy,
    line: { fill: "none", width: 0 },
    radius: 0,
  });
  addText(slide, title, {
    left: 56,
    top: 20,
    width: 930,
    height: 38,
    size: 30,
    bold: true,
    color: "#FFFFFF",
  });
  if (subtitle) {
    addText(slide, subtitle, {
      left: 58,
      top: 61,
      width: 1000,
      height: 20,
      size: 13,
      color: "#C8DCF0",
    });
  }
  addText(slide, `${String(pageNumber).padStart(2, "0")} / 12`, {
    left: 1150,
    top: 31,
    width: 74,
    height: 24,
    size: 14,
    color: "#C8DCF0",
    align: "right",
  });
  addLine(slide, 56, 690, 1168, "#D8E3EF", 1);
  addText(slide, "Week 2 / M2 · 2026-09-16", {
    left: 56,
    top: 699,
    width: 300,
    height: 16,
    size: 10,
    color: "#8393A6",
  });
}

function addMetricCard(slide, { left, top, width, value, label, accent = colors.blue, note = "" }) {
  addBox(slide, {
    left,
    top,
    width,
    height: 102,
    fill: colors.surface,
    line: { style: "solid", fill: colors.line, width: 1 },
    radius: 8,
  });
  addBox(slide, {
    geometry: "rect",
    left,
    top,
    width: 5,
    height: 102,
    fill: accent,
    line: { fill: "none", width: 0 },
    radius: 0,
  });
  addText(slide, value, {
    left: left + 20,
    top: top + 15,
    width: width - 36,
    height: 38,
    size: 30,
    bold: true,
    color: accent,
  });
  addText(slide, label, {
    left: left + 20,
    top: top + 56,
    width: width - 36,
    height: 24,
    size: 14,
    bold: true,
    color: colors.ink,
  });
  if (note) {
    addText(slide, note, {
      left: left + 20,
      top: top + 78,
      width: width - 36,
      height: 16,
      size: 10,
      color: colors.muted,
    });
  }
}

function addFooterNote(slide, text, color = colors.muted, left = 56, width = 1168, top = 649) {
  addBox(slide, {
    geometry: "rect",
    left,
    top,
    width,
    height: 32,
    fill: "#E9F0F7",
    line: { fill: "none", width: 0 },
    radius: 0,
  });
  addText(slide, text, {
    left: left + 14,
    top: top + 8,
    width: width - 28,
    height: 17,
    size: 11,
    color,
  });
}

function addImage(slide, relativePath, options) {
  return slide.images.add({
    blob: imageCache.get(relativePath),
    contentType: "image/png",
    alt: options.alt,
    fit: options.fit ?? "contain",
    position: {
      left: options.left,
      top: options.top,
      width: options.width,
      height: options.height,
    },
  });
}

function addBulletList(slide, items, options) {
  const paragraphs = items.map((item) => ({
    bulletCharacter: "•",
    marginLeft: 18 * 12700,
    indent: -10 * 12700,
    runs: [
      {
        run: item.lead ? `${item.lead} ` : "",
        textStyle: { bold: true, color: item.leadColor ?? colors.ink },
      },
      { run: item.text },
    ],
    spaceAfter: 240,
  }));
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: {
      left: options.left,
      top: options.top,
      width: options.width,
      height: options.height,
    },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text.set(paragraphs);
  shape.text.style = {
    typeface: FONT_FAMILY,
    fontSize: options.size ?? 17,
    color: colors.ink,
    autoFit: "shrinkText",
    wrap: "square",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return shape;
}

function addTable(slide, values, options) {
  const table = slide.tables.add({
    rows: values.length,
    columns: values[0].length,
    left: options.left,
    top: options.top,
    width: options.width,
    height: options.height,
    values,
    columnTracks: options.columnTracks,
  });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: colors.line, width: 1 });
  const headerRange = table.cells.block({
    row: 0,
    column: 0,
    rowCount: 1,
    columnCount: values[0].length,
  });
  headerRange.fill = colors.navy;
  headerRange.textStyle.color = "#FFFFFF";
  headerRange.textStyle.bold = true;
  headerRange.textStyle.fontSize = options.headerSize ?? 14;
  const bodyRange = table.cells.block({
    row: 1,
    column: 0,
    rowCount: values.length - 1,
    columnCount: values[0].length,
  });
  bodyRange.textStyle.fontSize = options.bodySize ?? 13;
  bodyRange.textStyle.color = colors.ink;
  if (options.alignments) {
    for (let column = 0; column < values[0].length; column += 1) {
      for (let row = 0; row < values.length; row += 1) {
        table.getCell(row, column).text.alignment = options.alignments[column] ?? "left";
      }
    }
  }
  for (let row = 0; row < values.length; row += 1) {
    for (let column = 0; column < values[0].length; column += 1) {
      table.getCell(row, column).text.style = {
        typeface: FONT_FAMILY,
        fontSize: row === 0 ? (options.headerSize ?? 14) : (options.bodySize ?? 13),
        bold: row === 0,
        color: row === 0 ? "#FFFFFF" : colors.ink,
      };
    }
  }
  return table;
}

function addSectionLabel(slide, text, left, top, color = colors.blue) {
  addText(slide, text, {
    left,
    top,
    width: 240,
    height: 22,
    size: 13,
    bold: true,
    color,
  });
}

const imageCache = new Map();
for (const relativePath of [
  "reports/clustering/elbow_plot.png",
  "reports/clustering/silhouette_plot.png",
  "reports/clustering/cluster_scatter_pca.png",
  "reports/modeling/model_comparison.png",
  "reports/modeling/roc_curves.png",
  "reports/rag/chunk_distribution.png",
  "reports/rag/retrieval_metrics.png",
  "reports/rag/top_k_sensitivity.png",
]) {
  imageCache.set(relativePath, await fs.readFile(path.join(workspaceDir, relativePath)));
}

// Slide 1: cover
{
  const slide = ppt.slides.add();
  slide.background.fill = colors.navyDeep;
  addBox(slide, {
    geometry: "rect",
    left: 0,
    top: 0,
    width: 1280,
    height: 720,
    fill: colors.navyDeep,
    line: { fill: "none", width: 0 },
    radius: 0,
  });
  addBox(slide, {
    geometry: "ellipse",
    left: 985,
    top: 0,
    width: 470,
    height: 310,
    fill: "#174C79",
    line: { fill: "none", width: 0 },
    radius: 0,
  });
  addBox(slide, {
    geometry: "ellipse",
    left: 1070,
    top: 560,
    width: 330,
    height: 310,
    fill: "#0E3A62",
    line: { fill: "none", width: 0 },
    radius: 0,
  });
  addText(slide, "WEEK 2 / M2", {
    left: 82,
    top: 74,
    width: 240,
    height: 24,
    size: 15,
    bold: true,
    color: "#79C8C1",
  });
  addText(slide, "基于全球远程招聘岗位大数据的\n岗位质量评分与人岗匹配研究", {
    left: 82,
    top: 142,
    width: 925,
    height: 144,
    size: 42,
    bold: true,
    color: "#FFFFFF",
  });
  addLine(slide, 84, 322, 540, "#4B7397", 2);
  addText(slide, "Week 2 汇报：人岗匹配 · 岗位聚类 · 多模型对比 · RAG · Agent", {
    left: 84,
    top: 350,
    width: 880,
    height: 34,
    size: 22,
    color: "#D7E6F4",
  });
  addText(slide, "数据：Himalayas 公开 Jobs API · 12,000 条全球远程岗位", {
    left: 84,
    top: 405,
    width: 760,
    height: 25,
    size: 15,
    color: "#A9C2D8",
  });
  addText(slide, "汇报日期：2026-09-17", {
    left: 84,
    top: 596,
    width: 300,
    height: 24,
    size: 14,
    color: "#A9C2D8",
  });
  addText(slide, "数据范围：全球远程岗位 · 每条记录保留 source_url、crawl_time、data_origin", {
    left: 84,
    top: 628,
    width: 800,
    height: 22,
    size: 12,
    color: "#6F91AD",
  });
  slide.speakerNotes.textFrame.setText(
    "开场可以说：这是 Week 2 中期汇报，围绕人岗匹配、岗位聚类、多模型对比、RAG 检索和 Agent 工具链，数据来自 12,000 条全球远程岗位。",
  );
}

// Slide 2: completion status
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 2, "Week 2 完成状态", "按课程表核对项目文件后的实际状态");
  addMetricCard(slide, {
    left: 56,
    top: 126,
    width: 270,
    value: "5 / 5",
    label: "Week 2 任务模块",
    accent: colors.teal,
    note: "均有代码、结果或报告",
  });
  addMetricCard(slide, {
    left: 347,
    top: 126,
    width: 270,
    value: "12,000",
    label: "清洗岗位记录",
    accent: colors.blue,
    note: "job_id 去重后无丢失",
  });
  addMetricCard(slide, {
    left: 638,
    top: 126,
    width: 270,
    value: "4",
    label: "聚类簇数量",
    accent: colors.orange,
    note: "候选 K=3 至 8",
  });
  addMetricCard(slide, {
    left: 929,
    top: 126,
    width: 295,
    value: "真实",
    label: "Agent 模型调用",
    accent: colors.red,
    note: "real_demo_output.json",
  });
  const rows = [
    ["任务", "当前状态", "主要证据"],
    ["人岗匹配", "已完成", "matching.py · matching_demo.json · 人岗匹配文档"],
    ["聚类与多模型对比", "已完成", "K-Means K=4 · 4 类和 10 张诊断/结果文件"],
    ["RAG 检索实验", "已完成", "FAISS + bge-small-zh-v1.5 · 55,984 Chunk · 12 题"],
    ["Agent 原型", "已完成", "Function Calling · 真实调用 JSON · Prompt v1"],
    ["中期汇报材料", "已完成", "多模型对比文档 · RAG 报告 · PPT 大纲"],
  ];
  addTable(slide, rows, {
    left: 56,
    top: 250,
    width: 1168,
    height: 300,
    columnTracks: [
      { mode: "fixed", value: 210 },
      { mode: "fixed", value: 130 },
      { mode: "fr", value: 1 },
    ],
    headerSize: 14,
    bodySize: 14,
    alignments: ["left", "center", "left"],
  });
  addBox(slide, {
    left: 56,
    top: 568,
    width: 1168,
    height: 88,
    fill: colors.softBlue,
    line: { fill: "#C9DFF2", width: 1 },
    radius: 8,
  });
  addText(
    slide,
    "这一页对应课程表的五项任务。每个模块都已经有代码、结果文件和提交文档；后面几页分别展开匹配公式、聚类选择、模型指标、RAG 召回和 Agent 调用过程。",
    {
      left: 78,
      top: 590,
      width: 1124,
      height: 48,
      size: 16,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：Week 2 五项都做完了，证据都在项目目录里。接下来按匹配、聚类、模型对比、RAG、Agent 的顺序展开。",
  );
}

// Slide 3: data and pipeline
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 3, "数据底座与 Week 2 技术链路", "同一份清洗数据支撑评分、匹配、聚类、检索与 Agent");
  addBox(slide, {
    left: 56,
    top: 128,
    width: 1168,
    height: 96,
    fill: colors.softBlue,
    line: { fill: "#C9DFF2", width: 1 },
    radius: 8,
  });
  addText(slide, "data/processed/jobs_cleaned.parquet", {
    left: 82,
    top: 149,
    width: 430,
    height: 25,
    size: 20,
    bold: true,
    color: colors.blue,
  });
  addText(slide, "12,000 条 · 62 列 · 全球远程岗位 · 保留 job_id / source_url / crawl_time / data_origin", {
    left: 82,
    top: 184,
    width: 800,
    height: 22,
    size: 15,
    color: colors.ink,
  });
  const stages = [
    ["01", "质量评分", "规则标签 + 四模型", colors.blue],
    ["02", "人岗匹配", "TF-IDF + 余弦", colors.teal],
    ["03", "岗位聚类", "SVD + K-Means", colors.orange],
    ["04", "RAG 检索", "BGE + FAISS", colors.red],
    ["05", "Agent", "Function Calling", "#7556A8"],
  ];
  for (let index = 0; index < stages.length; index += 1) {
    const x = 56 + index * 234;
    const [number, title, detail, accent] = stages[index];
    addBox(slide, {
      left: x,
      top: 248,
      width: 212,
      height: 250,
      fill: colors.surface,
      line: { fill: colors.line, width: 1 },
      radius: 8,
    });
    addText(slide, number, {
      left: x + 22,
      top: 274,
      width: 60,
      height: 28,
      size: 15,
      bold: true,
      color: accent,
    });
    addText(slide, title, {
      left: x + 22,
      top: 324,
      width: 170,
      height: 34,
      size: 22,
      bold: true,
      color: colors.ink,
    });
    addText(slide, detail, {
      left: x + 22,
      top: 376,
      width: 170,
      height: 42,
      size: 15,
      color: colors.muted,
    });
    addLine(slide, x + 22, 430, 168, colors.line, 1);
  }
  addBox(slide, {
    left: 56,
    top: 520,
    width: 1168,
    height: 120,
    fill: colors.softTeal,
    line: { fill: "#BDE2DA", width: 1 },
    radius: 8,
  });
  addText(
    slide,
    "五条分析链路共用同一份清洗数据。岗位质量评分、人岗匹配、岗位聚类、RAG 检索和 Agent 工具调用都从这份表出发；新结果写入 data/processed、reports、docs 或 submit，原始采集目录保持不动。",
    {
      left: 78,
      top: 548,
      width: 1124,
      height: 64,
      size: 16,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：后面所有模块都建立在同一份 12,000 条清洗岗位上，所以结果可以互相对照。",
  );
}

// Slide 4: matching and resume processing
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 4, "人岗匹配：简历输入处理与排序解释", "粘贴文本与文本型 PDF 都进入同一清洗和匹配流程");
  addBox(slide, {
    left: 56,
    top: 118,
    width: 545,
    height: 412,
    fill: colors.surface,
    line: { fill: colors.line, width: 1 },
    radius: 8,
  });
  addSectionLabel(slide, "简历输入处理", 82, 140, colors.teal);
  addBulletList(
    slide,
    [
      { lead: "粘贴文本：", text: "直接作为 UTF-8 文本进入 match_jobs，不保存原始简历到岗位数据目录。" },
      { lead: "PDF：", text: "pypdf 逐页执行 page.extract_text()，拼接后进入同一清洗流程。" },
      { lead: "扫描 PDF：", text: "如果没有可复制文本，系统会提示当前无法提取，暂不支持 OCR。" },
      { lead: "空输入：", text: "返回空结果，不执行无意义排序。" },
      { lead: "预处理：", text: "去 HTML/URL/标点，统一大小写，jieba 分词，技能别名归一化。" },
    ],
    { left: 82, top: 178, width: 490, height: 270, size: 15 },
  );
  addText(slide, "match_score = 0.55×技能 + 0.20×类别 + 0.15×经验 + 0.10×地点", {
    left: 82,
    top: 462,
    width: 490,
    height: 30,
    size: 15,
    bold: true,
    color: colors.teal,
  });
  addBox(slide, {
    left: 623,
    top: 118,
    width: 601,
    height: 412,
    fill: colors.surface,
    line: { fill: colors.line, width: 1 },
    radius: 8,
  });
  addSectionLabel(slide, "真实演示输出：Python、SQL、机器学习", 649, 140, colors.blue);
  addMetricCard(slide, {
    left: 649,
    top: 172,
    width: 255,
    value: "62.97",
    label: "最高匹配分",
    accent: colors.blue,
    note: "Data Science Expert",
  });
  addMetricCard(slide, {
    left: 923,
    top: 172,
    width: 255,
    value: "3",
    label: "命中技能",
    accent: colors.teal,
    note: "Python · SQL · ML",
  });
  addBox(slide, {
    left: 649,
    top: 290,
    width: 529,
    height: 91,
    fill: colors.softBlue,
    line: { fill: "#C9DFF2", width: 1 },
    radius: 8,
  });
  addText(slide, "Data Science Expert - Fully Remote", {
    left: 670,
    top: 308,
    width: 480,
    height: 24,
    size: 17,
    bold: true,
    color: colors.ink,
  });
  addText(
    slide,
    "mercor · Canada · USD 100-150 hourly · 匹配技能：machine learning、python、sql",
    { left: 670, top: 340, width: 486, height: 21, size: 13, color: colors.muted },
  );
  addText(slide, "来源可追溯", {
    left: 649,
    top: 402,
    width: 180,
    height: 24,
    size: 14,
    bold: true,
    color: colors.blue,
  });
  addText(
    slide,
    "https://himalayas.app/companies/mercor/jobs/data-science-expert-fully-remote-upto-150-hr-9231313173",
    { left: 649, top: 430, width: 525, height: 48, size: 11, color: colors.muted },
  );
  addBox(slide, {
    left: 56,
    top: 548,
    width: 1168,
    height: 108,
    fill: colors.softTeal,
    line: { fill: "#BDE2DA", width: 1 },
    radius: 8,
  });
  addText(
    slide,
    "匹配流程先统一处理简历文本，再计算技能、类别、经验和地点四个分项。现场演示用的是 Python、SQL、机器学习简历，最高匹配分为 62.97；结果会返回命中技能、缺失技能和原岗位链接，方便人工核对。",
    {
      left: 78,
      top: 570,
      width: 1124,
      height: 68,
      size: 16,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：左边是简历怎么进系统，右边是一次真实匹配结果。重点看分项权重、命中技能和来源链接。",
  );
}

// Slide 5: clustering method and K selection
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 5, "岗位聚类：K-Means 与 K 值选择", "先做文本向量化，再在压缩空间里比较不同 K");
  addImage(slide, "reports/clustering/elbow_plot.png", {
    left: 56,
    top: 128,
    width: 545,
    height: 330,
    alt: "K-Means 肘部法诊断图",
  });
  addImage(slide, "reports/clustering/silhouette_plot.png", {
    left: 623,
    top: 128,
    width: 601,
    height: 330,
    alt: "K-Means 轮廓系数诊断图",
  });
  addText(slide, "肘部观察：K=6", {
    left: 82,
    top: 470,
    width: 220,
    height: 24,
    size: 17,
    bold: true,
    color: colors.orange,
  });
  addText(slide, "轮廓最高：K=4（0.1976）", {
    left: 649,
    top: 470,
    width: 320,
    height: 24,
    size: 17,
    bold: true,
    color: colors.teal,
  });
  addBox(slide, {
    left: 56,
    top: 510,
    width: 1168,
    height: 146,
    fill: colors.softOrange,
    line: { fill: "#F2D6B0", width: 1 },
    radius: 8,
  });
  addText(slide, "综合选择 K=4", {
    left: 82,
    top: 530,
    width: 220,
    height: 28,
    size: 22,
    bold: true,
    color: colors.orange,
  });
  addText(
    slide,
    "候选 K 为 3 到 8。左边看 Inertia 下降趋势，折点附近偏向 K=6；右边看轮廓系数，K=4 最高。最终按可分性和业务可读性一起判断，选定 4 个岗位群组。",
    {
      left: 308,
      top: 534,
      width: 880,
      height: 92,
      size: 16,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：两张图给了不同信号，一个偏向 6，一个偏向 4。我们最后选了轮廓更高、也更好解释的 K=4。",
  );
}

// Slide 6: cluster projection and business names
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 6, "聚类可视化与业务命名", "二维图方便观察，四个名称来自高频技能和典型标题");
  addImage(slide, "reports/clustering/cluster_scatter_pca.png", {
    left: 56,
    top: 122,
    width: 640,
    height: 420,
    alt: "岗位聚类二维投影散点图",
  });
  addBox(slide, {
    left: 720,
    top: 122,
    width: 504,
    height: 420,
    fill: colors.surface,
    line: { fill: colors.line, width: 1 },
    radius: 8,
  });
  const clusterRows = [
    ["簇", "业务名称", "数量"],
    ["0", "云平台与 DevOps 工程岗位", "3,206"],
    ["1", "销售与业务拓展岗位", "8,070"],
    ["2", "企业应用与技术创新岗位", "243"],
    ["3", "机器学习与人工智能岗位", "481"],
  ];
  addTable(slide, clusterRows, {
    left: 744,
    top: 148,
    width: 456,
    height: 216,
    columnTracks: [
      { mode: "fixed", value: 45 },
      { mode: "fr", value: 1 },
      { mode: "fixed", value: 80 },
    ],
    headerSize: 13,
    bodySize: 13,
    alignments: ["center", "left", "right"],
  });
  addText(slide, "典型技能", {
    left: 744,
    top: 386,
    width: 220,
    height: 24,
    size: 15,
    bold: true,
    color: colors.blue,
  });
  addText(
    slide,
    "0：software engineer、cloud engineer\n1：sales、business development\n2：integration developer、devops engineer\n3：ai safety、ai evaluation、document review",
    { left: 744, top: 416, width: 456, height: 100, size: 13, color: colors.ink },
  );
  addBox(slide, {
    left: 56,
    top: 560,
    width: 1168,
    height: 96,
    fill: colors.softBlue,
    line: { fill: "#C9DFF2", width: 1 },
    radius: 8,
  });
  addText(
    slide,
    "销售与业务拓展岗位数量最大，云平台与 DevOps 次之；机器学习与企业应用两类规模更小。名称根据高频技能、主类别和典型标题整理，Cluster 2 样本较少，后续可以再抽样核对。",
    {
      left: 78,
      top: 582,
      width: 1124,
      height: 56,
      size: 16,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：左边看四类大致分开的样子，右边看每类叫什么、有多少。销售类最多，工程和 AI 类更集中。",
  );
}

// Slide 7: quality model
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 7, "岗位质量评分模型与四模型对比", "用岗位信息完整度规则生成标签，再比较四种分类器");
  addImage(slide, "reports/modeling/model_comparison.png", {
    left: 56,
    top: 128,
    width: 670,
    height: 400,
    alt: "四模型指标对比图",
  });
  const rows = [
    ["模型", "Accuracy", "F1", "ROC-AUC"],
    ["Logistic Regression", "0.8775", "0.8774", "0.9417"],
    ["SVM", "0.8729", "0.8732", "0.9381"],
    ["Random Forest", "0.8738", "0.8723", "0.9444"],
    ["XGBoost", "0.9142", "0.9140", "0.9662"],
  ];
  addTable(slide, rows, {
    left: 754,
    top: 180,
    width: 470,
    height: 230,
    columnTracks: [
      { mode: "fr", value: 1.7 },
      { mode: "fr", value: 1 },
      { mode: "fr", value: 1 },
      { mode: "fr", value: 1 },
    ],
    headerSize: 12,
    bodySize: 12,
    alignments: ["left", "right", "right", "right"],
  });
  addBox(slide, {
    left: 754,
    top: 426,
    width: 470,
    height: 100,
    fill: colors.softTeal,
    line: { fill: "#BDE2DA", width: 1 },
    radius: 8,
  });
  addText(slide, "当前主模型：XGBoost", {
    left: 776,
    top: 444,
    width: 430,
    height: 24,
    size: 17,
    bold: true,
    color: colors.teal,
  });
  addText(slide, "F1 0.9140 · ROC-AUC 0.9662", {
    left: 776,
    top: 476,
    width: 430,
    height: 24,
    size: 16,
    color: colors.ink,
  });
  addBox(slide, {
    left: 56,
    top: 552,
    width: 1168,
    height: 104,
    fill: colors.softBlue,
    line: { fill: "#C9DFF2", width: 1 },
    radius: 8,
  });
  addText(
    slide,
    "四个模型都在同一测试集上比较。Logistic Regression 和 SVM 适合作为可解释基线，Random Forest 能抓住非线性关系，XGBoost 的 F1 和 ROC-AUC 最高，因此作为当前岗位信息质量评分主模型。",
    {
      left: 78,
      top: 574,
      width: 1124,
      height: 64,
      size: 16,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：这一页看评分模块。四个模型横向比较后，XGBoost 表现最好，后面系统里也用它给岗位信息质量打分。",
  );
}

// Slide 8: multi-model comparison
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 8, "五个模块横向对比", "每个模块解决不同问题，评价方式也分开看");
  const rows = [
    ["模块", "业务目标", "输入 / 算法", "输出 / 评价", "当前状态"],
    ["质量评分", "衡量岗位信息完整度", "结构化特征 + 四分类器", "质量等级 / F1、AUC", "已完成 · XGBoost 最优"],
    ["人岗匹配", "按简历排序岗位", "简历与岗位 + TF-IDF 余弦", "匹配分 / 分项解释", "已完成 · 可演示"],
    ["岗位聚类", "发现岗位群组", "加权 TF-IDF + SVD + K-Means", "4 类 / 轮廓与业务命名", "已完成 · K=4"],
    ["RAG 检索", "自然语言找岗位", "BGE + FAISS Top-k", "岗位与来源 / Hit@3", "已完成 · Hit@3=50%"],
    ["Agent", "组合调用分析工具", "Function Calling + 本地工具", "结果和来源 / 调用链", "已完成 · 真实调用"],
  ];
  addTable(slide, rows, {
    left: 56,
    top: 128,
    width: 1168,
    height: 390,
    columnTracks: [
      { mode: "fixed", value: 120 },
      { mode: "fixed", value: 185 },
      { mode: "fr", value: 1.28 },
      { mode: "fr", value: 1.12 },
      { mode: "fr", value: 1.25 },
    ],
    headerSize: 13,
    bodySize: 12,
    alignments: ["left", "left", "left", "left", "left"],
  });
  addBox(slide, {
    left: 56,
    top: 540,
    width: 1168,
    height: 116,
    fill: colors.softBlue,
    line: { fill: "#C9DFF2", width: 1 },
    radius: 8,
  });
  addText(
    slide,
    "质量评分看分类指标，人岗匹配看排序和分项解释，聚类看群组结构，RAG 看召回效果，Agent 看工具调用过程。五个模块共用同一批本地岗位数据，但评价标准各自独立。",
    {
      left: 78,
      top: 566,
      width: 1124,
      height: 68,
      size: 16,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：这一页是总对照表。后面两页展开 RAG，再一页展开 Agent。",
  );
}

// Slide 9: RAG index
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 9, "RAG 知识库构建", "本地岗位文本分块后写入 BGE 向量索引");
  addMetricCard(slide, {
    left: 56,
    top: 128,
    width: 270,
    value: "12,000",
    label: "源岗位",
    accent: colors.blue,
  });
  addMetricCard(slide, {
    left: 347,
    top: 128,
    width: 270,
    value: "55,984",
    label: "分区感知 Chunk",
    accent: colors.teal,
  });
  addMetricCard(slide, {
    left: 638,
    top: 128,
    width: 270,
    value: "512",
    label: "Embedding 维度",
    accent: colors.orange,
  });
  addMetricCard(slide, {
    left: 929,
    top: 128,
    width: 295,
    value: "100%",
    label: "来源字段完整率",
    accent: colors.green,
  });
  addImage(slide, "reports/rag/chunk_distribution.png", {
    left: 56,
    top: 250,
    width: 540,
    height: 280,
    alt: "RAG Chunk 长度分布图",
  });
  addBox(slide, {
    left: 623,
    top: 250,
    width: 601,
    height: 280,
    fill: colors.surface,
    line: { fill: colors.line, width: 1 },
    radius: 8,
  });
  addSectionLabel(slide, "索引组成", 649, 270, colors.teal);
  addBulletList(
    slide,
    [
      { lead: "Embedding：", text: "BAAI/bge-small-zh-v1.5，512 维，本地模型文件。" },
      { lead: "向量库：", text: "FAISS IndexFlatIP，L2 归一化后做精确内积搜索。" },
      { lead: "Chunk：", text: "岗位介绍、职责、要求分区；无显式标题时使用综合回退块。" },
      { lead: "追踪：", text: "每条结果返回 job_id、source_url、crawl_time、data_origin。" },
      { lead: "基线：", text: "TF-IDF 基线保留作对照，正式方案是 BGE + FAISS。" },
    ],
    { left: 649, top: 304, width: 540, height: 200, size: 14.5 },
  );
  addBox(slide, {
    left: 56,
    top: 552,
    width: 1168,
    height: 104,
    fill: colors.softTeal,
    line: { fill: "#BDE2DA", width: 1 },
    radius: 8,
  });
  addText(
    slide,
    "知识库只使用本地清洗后的 12,000 条岗位。文本按岗位介绍、职责和要求分区切块，再写入 FAISS；每条召回结果都带回岗位编号和原链接，方便核对来源。",
    {
      left: 78,
      top: 574,
      width: 1124,
      height: 64,
      size: 16,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：RAG 这一页先讲库怎么建。55,984 个 Chunk 是主索引规模，Embedding 用的是本地 BGE 模型。",
  );
}

// Slide 10: RAG evaluation
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 10, "RAG 检索召回测试", "12 个测试问题，按 Top-3 统计命中情况");
  addMetricCard(slide, {
    left: 56,
    top: 128,
    width: 270,
    value: "50.00%",
    label: "Query Hit@3",
    accent: colors.teal,
    note: "6 / 12 题至少命中 1 条",
  });
  addMetricCard(slide, {
    left: 347,
    top: 128,
    width: 270,
    value: "0.3333",
    label: "Macro Precision@3",
    accent: colors.blue,
  });
  addMetricCard(slide, {
    left: 638,
    top: 128,
    width: 270,
    value: "0.4444",
    label: "Macro MRR@3",
    accent: colors.orange,
  });
  addMetricCard(slide, {
    left: 929,
    top: 128,
    width: 295,
    value: "1.0000",
    label: "来源字段完整率",
    accent: colors.green,
  });
  addImage(slide, "reports/rag/retrieval_metrics.png", {
    left: 56,
    top: 248,
    width: 650,
    height: 280,
    alt: "RAG 逐题检索 Precision@3 图",
  });
  addImage(slide, "reports/rag/top_k_sensitivity.png", {
    left: 738,
    top: 248,
    width: 486,
    height: 280,
    alt: "RAG Top-k 敏感性图",
  });
  addBox(slide, {
    left: 56,
    top: 548,
    width: 1168,
    height: 108,
    fill: colors.softBlue,
    line: { fill: "#C9DFF2", width: 1 },
    radius: 8,
  });
  addText(
    slide,
    "12 题里有 6 题在 Top-3 命中，Query Hit@3 为 50%。成功题包括 Q01、Q02、Q06、Q07、Q08、Q12。提高 Top-k 会提升命中率，但 Precision 会下降；逐题细节写在 RAG 实验报告中。",
    {
      left: 78,
      top: 570,
      width: 1124,
      height: 68,
      size: 16,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：左边看每道题的表现，右边看 Top-k 变化。50% 是 12 题里有一半至少命中一条。",
  );
}

// Slide 11: Agent
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 11, "Agent 工具调用演示", "模型选择工具，本地执行检索、评分和匹配");
  addBox(slide, {
    left: 56,
    top: 118,
    width: 355,
    height: 410,
    fill: colors.surface,
    line: { fill: colors.line, width: 1 },
    radius: 8,
  });
  addSectionLabel(slide, "工作流", 82, 140, colors.blue);
  const workflow = [
    ["1", "自然语言任务"],
    ["2", "模型选择工具"],
    ["3", "本地函数执行"],
    ["4", "结果与来源回填"],
    ["5", "最终回答"],
  ];
  for (let index = 0; index < workflow.length; index += 1) {
    const y = 178 + index * 58;
    addBox(slide, {
      geometry: "ellipse",
      left: 82,
      top: y,
      width: 40,
      height: 40,
      fill: index === 1 ? colors.blue : colors.softBlue,
      line: { fill: "none", width: 0 },
      radius: 0,
    });
    addText(slide, workflow[index][0], {
      left: 82,
      top: y + 10,
      width: 40,
      height: 20,
      size: 13,
      bold: true,
      color: index === 1 ? "#FFFFFF" : colors.blue,
      align: "center",
    });
    addText(slide, workflow[index][1], {
      left: 138,
      top: y + 8,
      width: 240,
      height: 28,
      size: 17,
      bold: index === 1,
      color: colors.ink,
    });
    if (index < workflow.length - 1) addLine(slide, 102, y + 42, 0, colors.line, 1);
  }
  addBox(slide, {
    left: 439,
    top: 118,
    width: 785,
    height: 410,
    fill: colors.surface,
    line: { fill: colors.line, width: 1 },
    radius: 8,
  });
  addSectionLabel(slide, "真实运行记录", 465, 140, colors.teal);
  addBox(slide, {
    left: 465,
    top: 172,
    width: 733,
    height: 56,
    fill: colors.softTeal,
    line: { fill: "#BDE2DA", width: 1 },
    radius: 8,
  });
  addText(slide, "model_call = true · gpt-5.6-sol · 3 turns · 3 tool calls", {
    left: 486,
    top: 190,
    width: 690,
    height: 24,
    size: 17,
    bold: true,
    color: colors.teal,
  });
  addSectionLabel(slide, "五类本地工具", 465, 248, colors.orange);
  const tools = [
    ["search_jobs", "关键词、技能、类别、地区"],
    ["score_job", "岗位信息质量分与等级"],
    ["match_resume", "简历匹配与分项解释"],
    ["cluster_summary", "聚类名称、技能、标题"],
    ["retrieve_jobs", "Top-k 检索与来源"],
  ];
  for (let index = 0; index < tools.length; index += 1) {
    const y = 284 + index * 44;
    addText(slide, tools[index][0], {
      left: 488,
      top: y,
      width: 165,
      height: 22,
      size: 14,
      bold: true,
      color: colors.blue,
    });
    addText(slide, tools[index][1], {
      left: 662,
      top: y,
      width: 505,
      height: 22,
      size: 13,
      color: colors.ink,
    });
  }
  addBox(slide, {
    left: 56,
    top: 548,
    width: 1168,
    height: 108,
    fill: colors.softTeal,
    line: { fill: "#BDE2DA", width: 1 },
    radius: 8,
  });
  addText(
    slide,
    "真实演示记录保存在 real_demo_output.json。模型完成工具选择后，本地依次执行 search_jobs 与 match_resume；返回结果带岗位、匹配分、质量分和来源链接。网络不可用时，也可以切换到本地规则路由继续演示。",
    {
      left: 78,
      top: 570,
      width: 1124,
      height: 68,
      size: 16,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：左边是调用流程，右边是一次真实运行。重点看 model_call=true 和五类工具。",
  );
}

// Slide 12: summary and next steps
{
  const slide = ppt.slides.add();
  addPageFrame(slide, 12, "Week 2 总结与 Week 3 衔接", "本周成果和下周联调方向");
  addBox(slide, {
    left: 56,
    top: 118,
    width: 575,
    height: 480,
    fill: colors.surface,
    line: { fill: colors.line, width: 1 },
    radius: 8,
  });
  addSectionLabel(slide, "Week 2 已完成", 82, 154, colors.teal);
  addBulletList(
    slide,
    [
      { lead: "人岗匹配：", text: "粘贴/PDF 输入、TF-IDF 余弦排序、分项解释、来源保留。" },
      { lead: "岗位聚类：", text: "K-Means、肘部与轮廓诊断、PCA 图、4 类业务命名。" },
      { lead: "多模型对比：", text: "评分、匹配、聚类、RAG、Agent 的目标、算法和输出对照。" },
      { lead: "RAG：", text: "BGE + FAISS 本地索引，12 题召回测试，全量来源回溯。" },
      { lead: "Agent：", text: "真实 Function Calling、5 类工具、Prompt v1。" },
    ],
    { left: 82, top: 197, width: 520, height: 360, size: 16 },
  );
  addBox(slide, {
    left: 653,
    top: 118,
    width: 571,
    height: 480,
    fill: colors.surface,
    line: { fill: colors.line, width: 1 },
    radius: 8,
  });
  addSectionLabel(slide, "现场演示建议", 679, 154, colors.orange);
  addBulletList(
    slide,
    [
      { lead: "先看数据：", text: "介绍 12,000 条岗位，以及来源链接和采集时间字段。" },
      { lead: "再看匹配：", text: "输入 Python/SQL/4 年/美国远程，解释分项与缺失技能。" },
      { lead: "聚类页：", text: "对比肘部 K=6 与轮廓 K=4，展示四类名称。" },
      { lead: "RAG：", text: "选择 Q12，展示 Top-3 和 source_url。" },
      { lead: "Agent：", text: "展示工具的调用链与真实 model_call=true。" },
    ],
    { left: 679, top: 197, width: 516, height: 360, size: 16 },
  );
  addBox(slide, {
    left: 56,
    top: 620,
    width: 1168,
    height: 36,
    fill: "#E9F0F7",
    line: { fill: "none", width: 0 },
    radius: 0,
  });
  addText(
    slide,
    "Week 3 方向：在现有 FastAPI + Streamlit 联调基础上，继续做接口稳定性和答辩材料。",
    {
      left: 78,
      top: 628,
      width: 1124,
      height: 22,
      size: 14,
      color: colors.ink,
    },
  );
  slide.speakerNotes.textFrame.setText(
    "可以说：Week 2 五项已经收束，现场可以按数据、匹配、聚类、RAG、Agent 的顺序演示；Week 3 接前后端联调。",
  );
}

const candidatePath = path.join(TMP_DIR, "Week2汇报.candidate.pptx");
await (await PresentationFile.exportPptx(ppt)).save(candidatePath);

const requirements = {
  explicitTotalSlideCount: 12,
  requiredNativeTableOwnerSlides: [2, 6, 7, 8],
  requiredNativeChartOwnerSlides: [],
  requiredEmbeddedWorkbookChartOwnerSlides: [],
  tableArithmeticContracts: [],
  materializeLiteralChartWorkbooks: false,
};

const stagingDir = path.join(workspaceDir, ".codex-finalizer", "week2");
await fs.mkdir(stagingDir, { recursive: true });

const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu",
    "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    ...[2, 6, 7, 8].flatMap((number) => ["--require-native-table-slide", String(number)]),
  ],
  fontPolicy: {
    basis: "design",
    families: [FONT_FAMILY],
    scriptFonts: { ea: FONT_FAMILY },
  },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "Week2汇报_可读版.validation.json"),
});

console.log(JSON.stringify(result, null, 2));
