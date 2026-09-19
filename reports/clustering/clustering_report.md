# 岗位聚类分析报告

## 1. 聚类目标

本分析使用清洗后的 12,000 条全球远程岗位，发现标题、技能、类别和描述中的岗位群组。结果用于岗位浏览、检索和人岗匹配解释，不代表劳动力市场中的唯一职业分类。

## 2. 特征与方法

- 文本字段：`job_title`、`skills_normalized`、`job_category`、`broad_category`、`description_clean`。
- 采用 TF-IDF 词与二元短语，标题和技能重复三次、类别重复两次，以表达业务上更重要的信号。
- 主模型为 K-Means：先将 TF-IDF 矩阵用 TruncatedSVD 压缩到 50 维，再在低维表示上聚类；原始 TF-IDF 中心用于提取可解释的高权重词。二维图使用同一 SVD 表示。
- 轮廓系数在最多 4,000 条固定随机样本上计算，降低大样本距离计算成本。

## 3. K 值选择

肘部代理选择 K=6，轮廓系数最高为 K=4，本次最终模型选择 K=4。完整数值见 `k_selection_metrics.csv`，图见 `elbow_plot.png` 与 `silhouette_plot.png`。

| K | Inertia | Silhouette |
| ---: | ---: | ---: |
| 3 | 2,095.08 | 0.1879 |
| 4 | 1,994.78 | 0.1976 |
| 5 | 1,910.10 | 0.1700 |
| 6 | 1,815.65 | 0.1677 |
| 7 | 1,759.07 | 0.1899 |
| 8 | 1,690.90 | 0.1926 |

## 4. 聚类结果与业务命名

### Cluster 0 云平台与 DevOps 工程岗位

岗位数量：3,206（26.7%）；主类别：Engineering。
高频标题：Senior Software Engineer、Senior Python Data Scraping Engineer (Freelance)、Freelance Agent Evaluation Engineer、Freelance Presentation Designer、React Engineer - Remote, Latin America。
主要技能：software engineer、backend development、fullstack development、cloud engineer、data engineering、backend engineering、platform engineering、devops engineer。
细分类别：Developer、Data Science、Design、Sales、Developer, Data Science。
解释：该类包含 3,206 个岗位，主要属于 Engineering。 高频文本特征包括：engineer、engineering、developer、software、senior。 名称依据主类别与高权重词生成，便于业务阅读。

### Cluster 1 销售与业务拓展岗位

岗位数量：8,070（67.2%）；主类别：Sales。
高频标题：Product Manager、Sales Development Representative、Business Development Representative、Account Executive、Account Manager。
主要技能：sales、business development、b2b sales、account management、customer service、digital marketing、operations、enterprise sales。
细分类别：Sales、Customer Service、Marketing、Operations、Product。
解释：该类包含 8,070 个岗位，主要属于 Sales。 高频文本特征包括：sales、manager、management、business、customer。 名称依据主类别与高权重词生成，便于业务阅读。

### Cluster 2 企业应用与技术创新岗位

岗位数量：243（2.0%）；主类别：Engineering。
高频标题：AI Innovation Engineer、SAP UX Developer、Windchill Middleware Developer、Distributed Systems Architect、Integration Platform Developer。
主要技能：software engineer、devops engineer、cloud engineer、platform engineering、backend engineer、site reliability engineering、data engineering、integration developer。
细分类别：Developer、Data Science、Data Science, Developer、Hardware Engineer、Hardware Engineer, Developer。
解释：该类包含 243 个岗位，主要属于 Engineering。 高频文本特征包括：vision technologies、bright vision、bright、teck、bv teck。 名称依据主类别与高权重词生成，便于业务阅读。

### Cluster 3 机器学习与人工智能岗位

岗位数量：481（4.0%）；主类别：Data Science。
高频标题：Business Ops Analyst - Fully Remote | Upto $160/hr、AI Safety Practitioner - Fully Remote | Upto $70/hr、Customer Support Expert - Fully Remote | Upto $160/hr、AI Safety Specialist - Remote | Upto $84/hr、GTM Analyst - Fully Remote | Upto $160/hr。
主要技能：ai safety specialist、document review、ai safety、ai evaluation、quality assurance、trust and safety、ai safety expert、ai safety researcher。
细分类别：Developer、Finance、Marketing、Data Science、Content Creator。
解释：该类包含 481 个岗位，主要属于 Data Science。 高频文本特征包括：ai interview、interview、resume、specialist、ai research。 名称依据主类别与高权重词生成，便于业务阅读。

## 5. 偏差与局限

样本明显偏向 Engineering 与 Data Science，聚类边界会受到平台岗位结构和原始类别字段的影响。K-Means 假设簇在 TF-IDF 空间中近似凸形，难以表达跨类别岗位；业务名称是基于高权重词的解释层，不是人工职业标准。后续可以对 Engineering 和 Data Science 分层聚类，并用人工抽样复核名称稳定性。

## 6. 可追溯输出

标签数据保存在 `data/processed/clustering/job_clusters.parquet`，每条记录保留 `job_id`、`source_url`、`crawl_time` 与 `data_origin`。
