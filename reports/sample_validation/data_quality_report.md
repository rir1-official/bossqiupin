# 数据质量报告

生成时间：2026-09-08T14:53:17.622777+00:00

## 数据范围

- 唯一输入：`data/raw/himalayas_api/2026-09-08/remote_all_*.jsonl`
- 分页文件：600 个
- 原始记录：200 条
- 去重后记录：200 条
- 重复记录：0 条（0.00%）
- 明确排除历史聚合文件：`data/raw/jobs_all.jsonl`

## 去重规则

按以下优先级保留首次出现记录：`source + job_id`、`source_url`、业务字段组合（岗位名、公司、城市、原始薪资、发布日期）。重复明细单独输出，不修改来源文件。

## 关键字段缺失

| 字段 | 原始类型 | 缺失数 | 缺失率 |
|---|---|---:|---:|
| `job_id` | str | 0 | 0.0% |
| `job_title` | str | 0 | 0.0% |
| `company_name` | str | 0 | 0.0% |
| `city` | str | 0 | 0.0% |
| `district` | str | 15 | 7.5% |
| `salary_raw` | str | 130 | 65.0% |
| `experience_raw` | str | 0 | 0.0% |
| `publish_date` | str | 0 | 0.0% |
| `job_description` | str | 0 | 0.0% |
| `skills` | str | 0 | 0.0% |
| `job_category` | str | 0 | 0.0% |
| `source` | str | 0 | 0.0% |
| `source_url` | str | 0 | 0.0% |
| `crawl_time` | str | 0 | 0.0% |
| `data_origin` | str | 0 | 0.0% |

来源 API 未提供的字段（`education`、`industry`、`company_type`、`company_size`、`longitude`、`latitude`）不列入上表，也不进入当前模型与图表；完整字段统计仍保留在 `data_quality_summary.json`。这些字段不做虚构填充。`salary_raw` 缺失也保留缺失标记。

## 解析与异常处理

- 薪资：解析币种、周期和上下限；年薪化系数为 hourly×2080、daily×260、weekly×52、monthly×12、annual×1。
- 跨币种：不使用外部汇率，不直接比较不同币种；图表和建模中的金额只采用 USD 年薪化字段。
- 异常值：年薪化小于 5,000 或大于 1,000,000，或上下限倒置，标记为异常但不覆盖原值。
- 薪资异常标记：3 条。
- 稳健分析值：对非异常 USD 年薪按样本内 P1/P99 缩尾，边界为 12,480.00 / 404,229.50 USD。
- 经验：来源职级映射为经验年限区间；该字段是分析代理，不是雇主明确要求年限。
- 文本：统一大小写和空白，移除 URL 与标点，使用 jieba 分词并过滤基础停用词。

## 验收检查

- 通过：`all_city_remote`
- 通过：`all_trace_fields_present`
- 未通过：`effective_records_at_least_10000`

## 标签说明

岗位质量分衡量的是“招聘信息透明度与完整度”，不是企业好坏、真实工作体验或录用概率。高质量标签为固定规则分数达到 80/100，供课程模型复现规则使用，不宣称是人工真实标签。
