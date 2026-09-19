# Week 3 前后端集成与联调说明

更新时间：2026-09-19

## 1. 集成目标

本周把同一份本地清洗岗位数据接入 FastAPI 后端和 Streamlit 前端，形成可现场演示的业务链路：

```text
输入简历 -> 文本/PDF解析 -> 人岗匹配 -> Top-k推荐 -> 本地岗位检索/聚类解释 -> Agent对话
```

后端不重新采集数据，只读取 `data/processed/jobs_cleaned.parquet`、本地聚类摘要和本地 RAG 索引。岗位记录继续保留 `source_url`、`crawl_time`、`data_origin`，`city=Remote` 仍是研究定义。

## 2. 后端 API

入口：`app/backend.py`；启动器：`app/run_api.py`。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 检查服务和岗位数据量 |
| POST | `/api/match` | 接收粘贴的简历文本，返回 Top-k 匹配岗位 |
| POST | `/api/match/upload` | 接收 TXT 或文本型 PDF，提取文本后复用同一匹配流程 |
| POST | `/api/score` | 按 `job_id` 或岗位标题查询岗位信息质量分 |
| POST | `/api/cluster` | 查询全部或指定聚类业务摘要 |
| GET | `/api/clusters` | 获取前端聚类画像列表 |
| POST | `/api/retrieve` | 使用 FAISS+BGE 本地索引检索岗位；不可用时返回错误，不回退到 TF-IDF |
| POST | `/api/chat` | 真实 OpenAI-compatible Function Calling，或显式选择本地规则 Agent |

API 文档可在 `http://127.0.0.1:8000/docs` 查看。

## 3. 简历输入处理

前端支持两种输入方式：

1. 直接粘贴简历文本；
2. 上传 `.txt` 或可复制文本层的 `.pdf`。

PDF 由 `pypdf.PdfReader` 逐页提取文本，随后和粘贴文本一样进入清洗、技能抽取、经验识别、类别推断和 TF-IDF+余弦相似度匹配。扫描 PDF 没有文本层时返回明确错误，不伪造 OCR 结果。原始简历不会写入岗位数据目录。

匹配结果包括 `match_score`、技能/类别/经验/地点分项、`matched_skills`、`missing_skills`、`quality_score`、`source_url`、`crawl_time` 和 `data_origin`。其中 `match_score` 是候选岗位排序参考，`quality_score` 仅表示岗位信息透明度与完整度，二者都不是录用概率。

## 4. Streamlit 前端

入口：`frontend/streamlit_app.py`；启动器：`app/run_frontend.py`。

界面采用克制的 Apple 风格：系统字体、浅灰背景、白色工作面板、清晰的蓝色主操作和明确的 loading/success/error 状态。三个工作页分别是：

- **匹配与推荐**：显示简历识别技能、经验代理、类别推断和 Top-k 岗位卡片；
- **岗位探索**：输入自然语言问题检索本地 RAG，并查看 K-Means 聚类画像；
- **Agent 对话**：输入复合任务，查看最终回答和工具调用链。

## 5. 启动方式

在项目根目录分别启动两个终端：

```bash
./scripts/python.sh -m app.run_api
./scripts/python.sh -m app.run_frontend
```

访问：

- 前端：`http://127.0.0.1:8501`
- API 文档：`http://127.0.0.1:8000/docs`

前端默认 API 请求超时为 180 秒；真实 Agent 单独使用 150 秒超时，避免首次模型响应较慢时页面提前结束。需要调整时可设置 `FRONTEND_API_TIMEOUT` 或 `FRONTEND_REAL_AGENT_TIMEOUT` 环境变量。Streamlit 主题配置位于 `.streamlit/config.toml`，用于保持 Apple 风格的蓝色主操作和浅色工作台背景。

项目使用 `.venv312` 和 `scripts/python.sh`，不要双击 `.py` 文件调用系统 Python.app。

## 6. Agent 模式边界

前端 toggle 打开时，请求 `/api/chat` 的 `use_real_model=true`，后端从当前运行环境读取已有 OpenAI-compatible 配置，仅在内存中使用凭据，不把 API Key 写入项目文件。模型负责自然语言理解、工具选择和最终回答，`search_jobs`、`score_job`、`match_resume`、`cluster_summary`、`retrieve_jobs` 工具仍由本地 Python 代码执行。

若接口或凭据不可用，页面应显示错误；只有用户主动关闭 toggle，才使用 `use_real_model=false` 的本地规则路由，并在返回中标记 `model_call=false`。本地模式不能冒充真实大模型调用。

## 7. 已知限制

- 首次加载 FAISS+BGE 模型可能较慢，服务进程会缓存本地 Agent 和 FAISS retriever，后续请求更快；
- 技能抽取依赖现有技能词典，未识别的同义词可能降低技能重合分；
- 扫描 PDF 尚未接入 OCR；
- RAG 结果是岗位检索证据，不替代人工判断；
- 当前已完成本地联调、接口回归测试、性能优化和 Docker 容器验证。首次构建拉取 python:3.12-slim 时因 Docker Hub 网络超时，随后使用本机已有 moodtune-pyspark:3.5.3 作为临时基础镜像完成构建；Dockerfile 默认基础镜像仍为 python:3.12-slim。api 与 frontend 容器已启动，API healthcheck 为 healthy，前端和 API 均可在本机访问。云端部署和在线地址尚未完成。
- 真实模型接口受网络和服务端响应时间影响；现场应提前完成一次真实调用，并保留 `reports/agent/real_demo_output.json` 作为可核验的备用记录。备用记录必须明确标注为已保存的真实调用结果，不能说成离线规则结果。
