# 项目指导与现有进度

更新时间：2026-09-08

## 一、项目建议定位

推荐继续使用：

> 基于全球远程招聘岗位大数据的岗位质量评分与人岗匹配研究

选择全球远程岗位的原因：Himalayas 提供公开、可分页的岗位 API，字段包含岗位名称、公司、薪资、职级、地点限制、技能类别和岗位描述，适合支撑评分、匹配、聚类和大模型四个模块。

需要在报告中明确：数据是全球远程招聘岗位，不等同于厦门或中国本地岗位；`city=Remote` 是研究对象定义，不是缺失值填充。

## 二、当前进度

| 模块 | 状态 | 说明 |
|---|---|---|
| 选题确认 | 已完成 | 已确定全球远程招聘岗位方向 |
| 数据源选择 | 已完成 | Himalayas 公开 Jobs API |
| 字段设计 | 已完成 | 见 `docs/data_dictionary.md` |
| 采集程序 | 已完成 | 支持游标分页、原始响应归档、状态续采和日志 |
| 原始采集 | 已完成 | 600 页，12,000 条 |
| 数据合并去重 | 待开始 | 用户要求暂不处理原始数据 |
| 数据清洗 | 待开始 | 薪资、经验、文本、异常值和重复值 |
| 可视化报告 | 待开始 | 目标至少 6 张有业务含义的图 |
| 评分模型 | 待开始 | 标签、训练/测试集、四类模型比较 |
| 人岗匹配文档 | 设计待落地 | TF-IDF + 余弦相似度为核心 |
| 数据看板 | 待开始 | 用于中期汇报演示 |
| 中期 PPT | 待开始 | 汇总采集、清洗、可视化、评分和匹配 |

## 三、建议执行路线

### 阶段 A：保留原始数据并建立处理副本

用户允许处理后，先运行只读统计，确认 12,000 条的字段分布和空值情况。随后将合并结果写入 `data/processed/jobs_all.jsonl`，不要写回 `data/raw/`。

### 阶段 B：清洗与特征工程

建议生成以下字段：

- `salary_min`、`salary_max`、`salary_avg`
- `experience_year_min`、`experience_year_max`
- `is_fresh_graduate`
- `skill_count`
- `description_length`
- `description_tokens`
- `quality_score` 或 `quality_label`

薪资需记录币种和周期，跨币种比较时应说明汇率或只在同币种内分析。岗位描述为空时不能简单填入“无”，应保留缺失标记。

### 阶段 C：岗位子集与标签

从 `job_title`、`skills`、`job_category`、`job_description` 中筛选 IT/数据岗位，例如 Python、SQL、Data、Analytics、Backend、AI、Machine Learning 等关键词。筛选规则需要写入报告并固定版本。

岗位质量标签可以由以下维度组成：

- 核心字段完整度
- 岗位描述长度和结构完整度
- 薪资透明度
- 技能要求清晰度
- 经验和职级信息完整度

推荐先构造规则标签，再用模型学习标签；同时承认这属于“岗位信息质量”而不是实际录用成功率。

### 阶段 D：可视化

每张图都要附三段文字：指标定义、图表观察、业务含义。避免只放漂亮的图而没有结论。优先使用可复现的 Python 脚本，并把图保存到 `reports/figures/`。

### 阶段 E：匹配算法

简历输入支持两种形式：粘贴文本和 PDF 提取文本。对简历与岗位描述采用同一套清洗、分词和技能词标准化流程。技能匹配使用 TF-IDF 向量和余弦相似度，再与类别、经验、地点等分项组合为总分。

建议输出：总匹配分、技能相似度、命中技能、缺失技能、经验差异、匹配解释和推荐岗位排序。

### 阶段 F：模型和看板

至少比较 Logistic Regression、SVM、Random Forest、XGBoost。线性模型展示系数，树模型展示特征重要性或 SHAP；报告中解释特征对结果的影响方向。

## 四、当前最重要的注意事项

- 原始数据现在是课程证据的一部分，不能覆盖。
- 12,000 条是采集量，不代表去重后的有效量；后续必须单独报告重复率和有效率。
- 不要把来源 API 的类别标签直接当作人工标注的真实技能；应注明字段来源。
- 评分标签要有规则和业务解释，不能为了提高准确率随意调整。
- 可视化必须说明洞察，模型必须说明可解释性。
- PPT 中应展示真实采集日志、字段样例、数据量统计和一个端到端匹配案例。

## 五、后续交付检查表

- [ ] 需求分析文档
- [ ] 数据字典和数据预处理文档
- [ ] 原始采集日志与数据来源说明
- [ ] 合并去重后的有效数据统计
- [ ] 至少 6 张可视化图和业务洞察
- [ ] 岗位质量评分模型及评估表
- [ ] 人岗匹配文档和演示样例
- [ ] 数据看板
- [ ] 中期汇报 PPT

## 六、第 1 周处理后状态（2026-09-08）

| 模块 | 状态 | 证据 |
|---|---|---|
| 数据合并与去重 | 已完成 | `data/processed/jobs_merged_deduplicated.jsonl`，12,000 条，0 条重复 |
| 清洗与特征工程 | 已完成 | `data/processed/jobs_cleaned.parquet`，包含薪资、经验、文本、jieba 分词和质量分特征 |
| 数据质量报告 | 已完成 | `reports/data_quality_report.md`，保留缺失原因和异常标记 |
| 可视化 | 已完成 | `reports/figures/` 7 张 PNG，`reports/visualization_report.md` |
| 岗位质量评分 | 已完成 | `reports/modeling/`，Logistic、SVM、Random Forest、XGBoost |
| 需求分析与中期材料 | 已完成 | `docs/requirements_analysis.md`、`reports/midterm_materials.md` |
| 人岗匹配实现 | 第 2 周 | 已完成设计文档，待实现 TF-IDF + 余弦相似度 |
| PPT 文件 | 按要求暂不制作 | 已准备中期汇报材料 |

## 七、Week 2 实际完成状态（2026-09-09）

上表保留为第 1 周历史记录；以下以当前文件为准：

| 模块 | 状态 | 证据 |
|---|---|---|
| 人岗匹配 | 已完成 | `src/job_analysis/matching.py`、`docs/matching_design.md`、`data/processed/matching_demo.json` |
| 岗位聚类 | 已完成并复跑 | `data/processed/clustering/job_clusters.parquet`；`reports/clustering/`；当前 K=4 |
| 多模型对比 | Markdown 已完成 | `reports/multi_model_comparison.md`；未覆盖既有 DOCX |
| RAG 检索原型 | 已完成 | `data/processed/rag/`；`reports/rag/retrieval_tests.json`；5 个测试问题 |
| Agent 原型 | 真实模型版与本地 fallback 已完成 | `src/job_analysis/agent.py`、`reports/agent/real_demo_output.json`、`docs/prompts/week2_agent_v1.md` |
| 中期汇报二 | 大纲已完成 | `submit/中期汇报二PPT大纲.md` |

聚类实现采用加权 TF-IDF -> TruncatedSVD(50 维) -> K-Means；报告同时记录肘部代理、轮廓系数最高 K 和综合选择规则。正式 RAG 使用 FAISS + BAAI/bge-small-zh-v1.5，另保留 TF-IDF 历史基线。Agent 同时提供真实 OpenAI-compatible Function Calling 和本地规则 fallback；真实运行记录中的 `model_call=true`，离线记录中的 `model_call=false`，两者不混淆。
