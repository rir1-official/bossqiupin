# RAG 知识库构建与检索召回测试实验

## 实验结论

本实验使用本地清洗后的 12,000 条 Himalayas 远程岗位数据，采用 BAAI/bge-small-zh-v1.5 生成 512 维中文语义向量，并写入 FAISS IndexFlatIP。主实验固定 Chunk=1200 字符、Overlap=200 字符、Top-k=3。所有结果均携带岗位编号、岗位名称、Chunk 编号、source_url、crawl_time 和 data_origin。

## 向量库选型

选择 FAISS 的原因是本实验为单机、离线、数万级 Chunk 的检索任务。IndexFlatIP 对归一化向量执行精确内积搜索，结果可重复且无需运行数据库服务。优点是部署简单、检索快、精确搜索没有近似索引损失；缺点是原生元数据过滤和多用户服务能力弱于 Chroma/Milvus，需要将 Parquet 元数据与向量行号共同维护。对于本项目的本地实验规模，这一取舍比引入服务端数据库更合适。

## 数据处理与入库

- 输入岗位：12000；去重后有效岗位：12000；删除重复岗位：0；删除残缺记录：0。
- 文本处理：HTML 解码、Unicode NFKC、控制字符与乱码替换、标签和多余空白清理。
- 长文本分块：优先在句号、问号、分号和换行处切分，超过上限时再在空格或标点处切分；相邻块保留 200 字符重叠。
- Chunk 数：55984；平均长度：970.0 字符；最大长度：1200 字符。
- 当前主索引采用分区感知策略：显式识别岗位介绍、岗位职责和任职要求后分别建块；无显式标题的岗位只建立一个综合文本回退块。参数对比表按完整清洗描述独立计算，用于比较 Chunk 设置，不代表主索引行数。
- Embedding：BAAI/bge-small-zh-v1.5，维度 512，向量 L2 归一化；FAISS 使用 IndexFlatIP。

## 主实验定量结果

| 指标 | 数值 |
| --- | ---: |
| 测试问题数 | 12 |
| Query Hit@3 | 0.5000 |
| Macro Precision@3 | 0.3333 |
| Macro Recall@3 | 0.0055 |
| Macro MRR@3 | 0.4444 |
| Macro nDCG@3 | 0.3529 |
| 来源字段完整率 | 1.0000 |

## 逐题结果

| ID | 类型 | Gold 岗位数 | 命中数 | P@3 | R@3 | 首条结果 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Q01 | 基础查询 | 363 | 1 | 0.3333 | 0.0028 | Lead Python Engineer |
| Q02 | 细节查询 | 209 | 2 | 0.6667 | 0.0096 | Nearshore Sector/ AWS Platform Engineer |
| Q03 | 基础查询 | 168 | 0 | 0.0000 | 0.0000 | Full Stack React Developer |
| Q04 | 细节查询 | 80 | 0 | 0.0000 | 0.0000 | Tableau CRM Business Analyst |
| Q05 | 模糊查询 | 303 | 0 | 0.0000 | 0.0000 | Test-Automation Engineer |
| Q06 | 细节查询 | 51 | 2 | 0.6667 | 0.0392 | Senior Data Engineer (PostgreSQL DBA) |
| Q07 | 模糊查询 | 939 | 1 | 0.3333 | 0.0011 | 現場服務工程師 / Field Service Engineer (Home Office, CN) |
| Q08 | 基础查询 | 1276 | 3 | 1.0000 | 0.0024 | Strategic Account Director |
| Q09 | 易混淆岗位查询 | 96 | 0 | 0.0000 | 0.0000 | Product Manager - ASO/SEO |
| Q10 | 易混淆岗位查询 | 284 | 0 | 0.0000 | 0.0000 | Data Scientist, FP&A Solutions |
| Q11 | 细节查询 | 236 | 0 | 0.0000 | 0.0000 | Senior Back-End Developer |
| Q12 | 模糊查询 | 264 | 3 | 1.0000 | 0.0114 | Staff, Machine Learning Engineer - BEV/Multi-Modal Perception |

## 成功与失败案例

成功案例：Q01、Q02、Q06、Q07、Q08、Q12。这些问题至少有一条 Top-3 结果满足预设的技能、类别或地区条件。

失败案例：Q03、Q04、Q05、Q09、Q10、Q11。失败表示 Top-3 未命中结构化 gold 集，不代表结果文本完全无关；可能原因包括中文职责表达与英文岗位语料跨语言差异、技能标签缺失、同义岗位边界和单向量检索未使用结构化过滤。

## 参数影响

参数对比口径说明：下表对每条完整清洗岗位描述独立计算不同 Chunk/Overlap 设置，目的是比较结构性开销；当前主索引采用岗位介绍、岗位职责和任职要求分区建块，并对无显式标题的岗位使用一个综合文本回退块，因此表中的 Chunk 数不能直接替代主索引 Chunk 数。

| Chunk/Overlap | Chunk 数 | 平均长度 | 短块比例 |
| --- | ---: | ---: | ---: |
| 800/120 | 104565 | 665.0 | 0.0538 |
| 1200/200 | 69252 | 1011.8 | 0.0502 |
| 1600/250 | 51376 | 1337.6 | 0.0600 |

800/120 产生更多向量，细粒度更高但上下文更短、存储和编码开销更大；1600/250 向量更少、上下文更完整，但主题混合风险更高。1200/200 在本数据平均描述长度约数千字符的条件下取得折中。Top-k 从 1 增至 5 通常提高命中率和召回率，但会降低结果精度并增加阅读成本，因此主实验固定 k=3。

FAISS IndexFlatIP 在本实验使用精确搜索，不引入近似索引召回损失；Embedding 决定中文查询与英文岗位描述之间的语义映射质量。后续可比较多语 Embedding、混合检索与结构化过滤，但本报告只记录当前实际运行结果。

## 输出文件

- `data/processed/rag/faiss.index`
- `data/processed/rag/chunks.parquet`
- `data/processed/rag/chunk_metadata.jsonl`
- `data/processed/rag/index_manifest.json`
- `reports/rag/test_queries.json`
- `reports/rag/retrieval_tests.json`
- `reports/rag/question_answer_source_triples.csv`
- `reports/rag/rag_eval_summary.json`
- `reports/rag/retrieval_metrics.png`
- `reports/rag/top_k_sensitivity.png`
- `reports/rag/chunk_distribution.png`
- `reports/rag/chunk_parameter_comparison.png`
