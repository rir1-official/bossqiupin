# 招聘岗位数据字典

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---:|---|
| job_id | string | 否 | 来源站点岗位唯一标识 |
| job_title | string | 是 | 岗位名称 |
| company_name | string | 是 | 招聘企业名称 |
| city | string | 是 | 工作城市 |
| district | string | 否 | 工作区县 |
| salary_raw | string | 否 | 来源页面原始薪资文本 |
| experience_raw | string | 否 | 来源页面原始经验要求 |
| education | string | 否 | 学历要求；当前 Himalayas API 未提供，保留为空，仅用于统一字段审计 |
| publish_date | string | 否 | 发布日期或更新时间 |
| job_description | string | 否 | 岗位职责、任职要求等原文 |
| industry | string | 否 | 所属行业；当前 Himalayas API 未提供，保留为空，仅用于统一字段审计 |
| company_type | string | 否 | 企业性质；当前 Himalayas API 未提供，保留为空，仅用于统一字段审计 |
| company_size | string | 否 | 企业规模；当前 Himalayas API 未提供，保留为空，仅用于统一字段审计 |
| skills | string/list | 否 | 技能标签或从描述中提取的技能 |
| job_category | string | 否 | 来源分类或项目归类 |
| longitude/latitude | number | 否 | 岗位地理坐标；全球远程岗位无固定办公坐标，当前 API 未提供，保留为空 |
| source | string | 是 | 数据来源名称 |
| source_url | string | 是 | 公开来源页面或详情链接 |
| crawl_time | string | 是 | ISO 8601 抓取时间 |
| data_origin | string | 是 | 固定为 self_crawled 或 public_dataset |

清洗阶段补充 `salary_min`、`salary_max`、`salary_avg`、`experience_year_min`、`experience_year_max`、`is_fresh_graduate`、`skill_count` 与 `description_length`。

说明：上述 6 个来源未提供字段不进入教师查看版 CSV、当前模型或可视化分析；完整标准字段和缺失计数仍保留在处理数据与 `reports/data_quality_summary.json` 中，便于审计和后续更换数据源时兼容字段结构。

## 清洗后派生字段

| 字段 | 类型 | 说明 |
|---|---|---|
| raw_page_file / raw_line_number | string / integer | 原始分页文件与行号 |
| salary_currency / salary_period | string | 解析后的币种和周期 |
| salary_min / salary_max / salary_avg | number | 原周期薪资数值 |
| salary_min_annual / salary_max_annual / salary_avg_annual | number | 固定工时假设下的年薪化数值，不用于跨币种比较 |
| salary_avg_usd_annual_winsorized | number | 仅 USD 非异常记录的 P1/P99 缩尾分析值 |
| salary_parse_status / salary_outlier | string / boolean | 薪资解析状态与异常标记 |
| experience_level_primary | string | 来源职级的主类别 |
| experience_year_min / experience_year_max | number | 按固定规则从职级映射的经验年限代理 |
| is_fresh_graduate | boolean | 来源职级是否包含 Entry-level |
| description_clean / description_tokens | string | 清洗文本和 jieba 分词结果 |
| description_length / description_word_count | integer | 描述字符数和空格分词数 |
| description_structure_count | integer | 职责、要求、福利等结构词命中数 |
| skills_normalized / skill_count | string / integer | 规范化技能和技能数 |
| location_restriction_count | integer | 允许申请的国家或地区数 |
| publish_age_days | integer | 截至本次采集时点的发布天数 |
| broad_category / is_it_data_role | string / boolean | 宽类岗位映射及工程/数据子集标记 |
| quality_score / quality_label / quality_level | number / integer / string | 岗位信息质量规则分、二分类标签和展示等级 |

## Himalayas API 映射

本项目取得授权后使用 Himalayas 公开岗位 API 作为主数据源。研究对象为全球远程 IT 岗位，因此 `city` 统一填入 `Remote`，`district` 保存岗位的 `locationRestrictions`（国家或地区限制），不将远程职位伪造为具体中国城市。

| API 字段 | 项目字段 | 处理方式 |
|---|---|---|
| guid / applicationLink | job_id, source_url | 用来源链接生成稳定 ID，同时保留原链接追溯来源 |
| title | job_title | 原样保留 |
| companyName | company_name | 原样保留 |
| minSalary, maxSalary, currency, salaryPeriod | salary_raw | 拼接为原始薪资文本，后续解析为数值特征 |
| seniority | experience_raw | 作为经验/职级要求 |
| locationRestrictions | district | 多地区用逗号连接 |
| categories, parentCategories | skills, job_category | 作为岗位技术标签和类别 |
| description / excerpt | job_description | HTML 转纯文本后保存 |
| pubDate | publish_date | Unix 时间戳转换为 UTC ISO 8601 |
