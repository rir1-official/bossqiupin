# 招聘岗位大数据采集器

用于课程项目的招聘岗位采集、落盘、合并去重和质量验收。当前主课题为“基于全球远程招聘岗位大数据的岗位质量评分与人岗匹配研究”。采集完成后按岗位类别与技能标签提取 IT/数据岗位子集，支撑评分、匹配、聚类和大模型模块。

## 安装与运行

项目统一使用仓库内的 `.venv`，不要通过 Finder 双击 `.py` 文件，也不要直接调用 macOS Command Line Tools 的系统 Python。首次使用先创建环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

之后统一通过稳定启动器运行。该入口会设置 `PYTHONPATH`，并规避 macOS 上 PyTorch CPU/OpenMP 多线程导致的解释器崩溃：

```bash
./scripts/python.sh --version
./scripts/python.sh -m unittest discover -s tests -v
./scripts/python.sh -m job_crawler.cli --help
```

先复制 `config/sites.example.json` 为 `config/sites.json`，根据已核验的公开站点填写 URL、分页参数及 JSON 字段路径。不要填写需要登录、验证码或明确禁止自动访问的页面。

```bash
./scripts/python.sh -m job_crawler.cli crawl --config config/sites.json --max-pages 3
./scripts/python.sh -m job_crawler.cli merge --raw-dir data/raw --output data/raw/jobs_all.jsonl
./scripts/python.sh -m job_crawler.cli quality --input data/raw/jobs_all.jsonl --report reports/crawl_quality_report.md
```

取得 Himalayas 对本课程研究用途的许可后，使用其公开 API 的游标分页采集 10,000 条：

```bash
./scripts/python.sh -m job_crawler.cli crawl-himalayas --target-records 10000 --delay-seconds 1
./scripts/python.sh -m job_crawler.cli merge --raw-dir data/raw --output data/raw/jobs_all.jsonl
./scripts/python.sh -m job_crawler.cli quality --input data/raw/jobs_all.jsonl --report reports/crawl_quality_report.md
```

采集进度写入 `logs/himalayas_state.json`。意外中断后执行相同命令会从上个成功页的游标继续，不重复从第一页开始。

## 数据链路

`crawl` 将每一页标准化记录落盘到 `data/raw/{source}/{date}/{city}_{keyword}_{page}.jsonl`，并将原始公开接口响应归档到 `data/raw_responses/`，同时追加 `logs/crawl_log.csv`。`merge` 会基于来源、岗位 ID 或岗位关键字段去重。`quality` 计算数据量、字段完整率、重复率和城市/关键词分布。

## 合规边界

- 仅访问无需登录的公开页面；遵守站点条款和 robots 规则。
- 已获授权的 Himalayas API 采集使用 `authorized_api_collection` 标记，并保留 API 来源链接和抓取时间。
- 不处理验证码、不绕过访问限制、不访问用户账户数据。
- 出现登录页、验证码、403 或 429 时，该来源会被停用并写入日志。
- 默认请求间隔为 2 至 5 秒，每个关键词完成后暂停 60 至 120 秒；课堂演示可通过配置缩短，但真实采集不得取消限速。

## Week 2 当前入口

Week 2 已基于 `data/processed/jobs_cleaned.parquet` 完成人岗匹配、岗位聚类、多模型对比、FAISS 中文 Embedding 检索实验和本地规则路由 Agent。聚类结果、K 值诊断图和业务摘要位于 `reports/clustering/`；正式 FAISS 索引位于 `data/processed/rag/`；旧 TF-IDF 版本仅保留为基线；对比说明位于 `reports/multi_model_comparison.md`；汇报大纲位于 `submit/中期汇报二PPT大纲.md`。

Python 崩溃诊断与正确启动方式见 [`docs/python_runtime.md`](docs/python_runtime.md)。如果 macOS 弹出“Python 意外退出”，通常是 Finder 双击 `.py` 调用了系统 `Python.app`；请在项目根目录使用 `./scripts/python.sh`。

```bash
./scripts/python.sh -m unittest discover -s tests -v
./scripts/python.sh -m job_analysis.clustering
HF_HUB_OFFLINE=1 ./scripts/python.sh -m job_analysis.rag_faiss search "Python 和 SQL 数据分析岗位" --top-k 3 --device auto
./scripts/python.sh -m job_analysis.agent --top-k 3
./scripts/python.sh scripts/create_week2_report.py --no-docx
```

聚类采用加权 TF-IDF -> TruncatedSVD(50 维) -> K-Means，当前综合选择 K=4。正式 RAG 实验使用 `BAAI/bge-small-zh-v1.5` 生成 512 维 Embedding，并通过 FAISS `IndexFlatIP` 检索；这与旧 TF-IDF 基线严格区分。Agent 输出 `model_call=false`，表示没有调用外部大模型。

## Week 3 本地系统演示

已新增 FastAPI + Streamlit 前后端联调入口，使用同一份本地清洗岗位数据打通“上传简历 -> 匹配 -> 推荐 -> 检索/聚类 -> Agent 对话”。

```bash
# 终端 1
./scripts/python.sh -m app.run_api

# 终端 2
./scripts/python.sh -m app.run_frontend
```

访问 `http://127.0.0.1:8501` 使用前端，访问 `http://127.0.0.1:8000/docs` 查看 API。支持粘贴简历文本以及 TXT/可复制文本型 PDF 上传；真实模型开关打开时使用 OpenAI-compatible Function Calling，关闭时才使用明确标记的本地规则 Agent。联调说明见 [`docs/week3_integration.md`](docs/week3_integration.md)，现场演示顺序见 [`submit/Week3现场演示脚本.md`](submit/Week3现场演示脚本.md)。

## 首日站点核验清单

1. 在浏览器中手动确认列表页公开可访问、可翻页且页面含岗位详情链接。
2. 记录列表接口或页面 URL、总页数、岗位 JSON 字段及详情接口。
3. 先用 `max_pages=2` 小样本运行，检查岗位名称、城市和来源链接完整率。
4. 小样本通过后，再按城市和关键词分批运行；每批完成后先执行 `merge` 和 `quality`。

字段定义见 `docs/data_dictionary.md`，可直接用于《需求分析文档》和《数据预处理文档》。

## 第 1 周分析流程

原始采集完成后，在项目内创建隔离环境并安装分析依赖：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

先用 200 条记录验证清洗逻辑，再运行全量流程：

```bash
./scripts/python.sh -m job_analysis.cleaning --sample-size 200
./scripts/run_week1.sh
```

处理程序只接受 `data/raw/himalayas_api/2026-09-08/remote_all_*.jsonl`，明确排除历史聚合文件 `data/raw/jobs_all.jsonl`。派生数据写入 `data/processed/`，教师查看版写入 `export/`，图表与质量报告写入 `reports/`。

macOS 上 XGBoost 需要 OpenMP。上述脚本会优先复用 scikit-learn wheel 中的 `libomp.dylib`，避免修改系统目录。

旧的 `job_crawler.cli merge --raw-dir data/raw` 仅保留为历史采集流程示例，不适用于本次数据：它会扫描到历史 `data/raw/jobs_all.jsonl`。当前应使用当天固定的 `job_analysis.cleaning` 与 `scripts/run_week1.sh` 入口。
