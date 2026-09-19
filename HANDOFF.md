# 项目交接说明

更新时间：2026-09-19

## 项目定位

项目题目：**基于全球远程招聘岗位大数据的岗位质量评分与人岗匹配研究**。

统一数据源为 Himalayas 公开 Jobs API。研究对象是全球远程招聘岗位，`city=Remote` 是研究定义，不是缺失值填充；`district` 保留 API 返回的地区限制。

## 当前真实状态

| 模块 | 状态 | 主要证据 |
|---|---|---|
| 原始采集 | 已完成 | 12,000 条、600 页；`data/raw/`、`data/raw_responses/`、`logs/` |
| 合并去重与清洗 | 已完成 | `data/processed/jobs_cleaned.parquet`，12,000 条；保留追溯字段 |
| 可视化 | 已完成 | `reports/figures/` 7 张图；`reports/visualization_report.md` |
| 岗位质量评分 | 已完成 | `reports/modeling/model_metrics.csv`；XGBoost F1=0.9140、ROC-AUC=0.9662 |
| 人岗匹配 | 已完成 | `src/job_analysis/matching.py`、`docs/matching_design.md`、`data/processed/matching_demo.json` |
| 岗位聚类 | 已完成并复跑 | `data/processed/clustering/`、`reports/clustering/`；当前选择 K=4 |
| 多模型对比 | Markdown 已完成 | `reports/multi_model_comparison.md`；DOCX 不在本次覆盖范围 |
| RAG 检索实验 | 已完成 | FAISS + BAAI/bge-small-zh-v1.5；当前分区感知索引 55,984 个 Chunk；12 个测试问题；`reports/rag/` |
| Agent 原型 | 已完成真实模型版与本地 fallback | JSON Schema、Prompt v1、真实 Chat Completions/Responses 入口、规则路由 fallback；真实记录见 `reports/agent/real_demo_output.json` |
| 中期汇报二材料 | 大纲已完成 | `submit/中期汇报二PPT大纲.md` |
| Week 3 前后端集成 | 本地联调已完成 | `app/backend.py`、`frontend/streamlit_app.py`、`tests/test_week3_api.py`；FastAPI + Streamlit 已打通简历输入、匹配、推荐、检索、聚类和 Agent 对话 |

## Week 2 实现口径

- 聚类：岗位文本加权 TF-IDF；先用 TruncatedSVD 压缩到 50 维，再用 K-Means；候选 K=[3,4,5,6,7,8]。当前报告记录肘部代理 K=6、轮廓最高 K=4、综合选择 K=4。原始 TF-IDF 中心用于解释高频技能/标题。
- 匹配：沿用既有 TF-IDF + 余弦相似度和 55/20/15/10 权重。匹配分是排序参考，不是录用概率。
- RAG：仅使用本地 `jobs_cleaned.parquet`。正式实验为 FAISS + BAAI/bge-small-zh-v1.5 中文 Embedding 检索；TF-IDF 仅作为历史基线。当前索引包含 55,984 个分区感知 Chunk：有显式标题的岗位按岗位介绍、岗位职责、任职要求分别建块；没有显式标题的岗位使用一个综合文本回退块，避免重复索引。测试共 12 个问题，Query Hit@3 为 50.00%，该结果来自规则条件金标准，不等同于人工标注真实 Recall；每条结果返回 `source_url`、`crawl_time`、`data_origin`。参数对比图中的 104,565、69,252 和 51,376 是对完整清洗描述的结构性 Chunk 对照，不是当前分区感知主索引数量。
- Python 稳定性：macOS Command Line Tools Python 3.9.6 在 PyTorch CPU/OpenMP 多线程 Embedding 路径出现过原生 `SIGSEGV`。`rag_faiss.py` 默认 `device=auto`，Apple Silicon 优先 MPS；`scripts/python.sh` 统一设置单线程 CPU fallback、KMP 线程参数和 MPS fallback。项目命令应通过该脚本运行，不要双击 `.py` 文件；详细诊断见 `docs/python_runtime.md`。
- Agent：默认支持真实 OpenAI-compatible Function Calling；当前 Codex 配置已完成一次真实调用，工具包括 `search_jobs`、`score_job`、`match_resume`、`cluster_summary`、`retrieve_jobs`。工具仍只执行本地岗位数据和本地索引。无凭据时可用 `--mode local` 离线 fallback，且不会把 fallback 标成真实模型调用。

## 常用验证命令

```bash
./scripts/python.sh -m unittest discover -s tests -v
./scripts/python.sh -m job_analysis.clustering
HF_HUB_OFFLINE=1 ./scripts/python.sh -m job_analysis.rag_faiss search "Python 和 SQL 数据分析岗位" --top-k 3 --device auto
./scripts/python.sh -m job_analysis.agent --mode real --top-k 3 --output reports/agent/real_demo_output.json
./scripts/python.sh scripts/create_week2_report.py --no-docx
```

## 重要约束

1. 不修改、删除或覆盖 `data/raw/`、`data/raw_responses/`。
2. 不重新采集 12,000 条数据，不更换 Himalayas 数据源。
3. 所有派生结果写入 `data/processed/`、`reports/`、`docs/` 或 `submit/`。
4. 所有岗位记录保留 `source_url`、`crawl_time`、`data_origin`。
5. 不把岗位质量分说成企业信誉或录用概率；不把 TF-IDF 说成深度学习。

## Week 3 当前状态（截至 2026-09-19）

- **本地前后端集成已完成**：FastAPI 后端封装评分、匹配、聚类、检索和对话接口；Streamlit 前端提供 Apple 风格工作台，打通“上传简历 -> 匹配 -> 推荐 -> 检索/聚类 -> Agent 对话”。
- **联调与测试证据**：`tests/test_week3_api.py` 的 13 项接口测试已通过；全量测试共 27 项、0 失败；浏览器已验证首屏、匹配页、岗位探索页和本地 Agent 页；真实 `/api/chat` 已验证返回 `model_call=true` 的 OpenAI-compatible Chat Completions 结果。
- **启动命令**：`./scripts/python.sh -m app.run_api` 与 `./scripts/python.sh -m app.run_frontend`；详细说明见 `docs/week3_integration.md`，现场步骤见 `submit/Week3现场演示脚本.md`。
- **测试与优化报告**：已完成并提交 `submit/测试报告.docx`，Markdown 证据见 `reports/week3/test_report.md`；预热后 Top-5 匹配中位数约 0.1705 秒。
- **AI 使用说明与反思报告**：已完成并提交 `submit/AI使用说明与反思报告.docx`，明确项目方案、主要算法逻辑和前端视觉由项目负责人主导，AI 仅辅助部分代码、调试、测试和文档。
- **Week 3 部署状态**：本地 Docker 镜像已构建并启动。首次拉取默认 python:3.12-slim 时 Docker Hub 超时，后使用本机已有 moodtune-pyspark:3.5.3 作为临时基础镜像完成 ARM64 本地验证；Dockerfile 默认基础镜像未改变。api 容器 healthcheck 为 healthy，/api/health 返回 12,000 条数据，frontend 容器可访问 http://127.0.0.1:8501。
- **剩余 Week 3 工作**：云端部署和在线地址、最终答辩 PPT 与模拟答辩仍未完成；测试报告、AI 使用说明与反思报告、部署手册和本地容器验证已完成。
