# Himalayas 授权 API 采集设计

## 课题范围

课题名称：**基于全球远程招聘岗位大数据的岗位质量评分与人岗匹配研究**。

主数据源为已获课程研究用途许可的 Himalayas 公开岗位 API。采集全行业远程岗位作为统一数据底座；后续使用 `skills`、`job_category`、`job_title` 与 `job_description` 筛选 IT/数据岗位子集，避免在采集阶段因关键词过滤遗漏岗位。

## 字段与追溯

每条标准化记录保存 `job_id`、`job_title`、`company_name`、`city`、`district`、`salary_raw`、`experience_raw`、`publish_date`、`job_description`、`skills`、`job_category`、`source`、`source_url`、`crawl_time`、`data_origin`。

- `city` 固定为 `Remote`；`district` 保存国家或地区限制。
- `job_id` 由公开岗位链接的 SHA-256 摘要生成，支持跨页稳定去重。
- `source_url` 保留原始岗位链接；`crawl_time` 记录 UTC 采集时间。
- `data_origin` 固定为 `authorized_api_collection`，与后续可能引入的数据集或人工样本清晰区分。

## 采集流程

1. 从 `https://himalayas.app/jobs/api` 获取首批数据。
2. 使用响应内的 `nextCursor` 请求下一页，避免 offset 翻页的重复记录。
3. 每页归档原始 JSON 至 `data/raw_responses/`，并输出标准化 JSONL 至 `data/raw/`。
4. 每页写入 `logs/crawl_log.csv`，同时更新 `logs/himalayas_state.json`。中断后使用同一命令从已保存游标继续。
5. 采集到 10,000 条后合并去重并生成质量报告。

## 验收

- 原始岗位记录不少于 10,000 条。
- 以 `source + job_id` 去重，保留来源链接与抓取时间。
- 岗位名称、公司、远程地点标识、来源链接完整率不低于 95%。
- 岗位描述或薪资至少一项完整率不低于 85%。
