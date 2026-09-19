# 数据预处理文档

## 1. 处理目标与边界

本流程只读取 `data/raw/himalayas_api/2026-09-08/` 下 600 个 `remote_all_*.jsonl` 分页文件。`data/raw/jobs_all.jsonl` 是历史聚合文件，明确排除。原始 JSONL 和 API 响应不修改、不覆盖、不删除，所有结果写入 `data/processed/`、`export/`、`reports/` 或 `docs/`。

数据研究对象为全球远程岗位，`city=Remote` 保持来源语义；`district` 表示岗位允许申请的国家或地区限制。

## 2. 合并与去重

- 合并前：200 条，600 个分页文件。
- 去重后：200 条。
- 重复：0 条，重复率 0.00%。
- 去重键依次为 `source + job_id`、`source_url`、岗位名/公司/城市/薪资/发布日期组合。
- 每条结果保留 `source_url`、`crawl_time`、`data_origin`，并增加 `raw_page_file` 和 `raw_line_number` 便于回溯。

## 3. 缺失值

不把“未提供”伪造成业务值。文本字段保留空字符串，数值解析字段保留空值，并添加 `salary_parse_status`、`experience_parse_status` 等状态字段。来源 API 未提供的学历、行业、公司性质、公司规模和经纬度保持为空。薪资缺失不以 0 填充。

## 4. 字段标准化与特征工程

| 新字段 | 含义 |
|---|---|
| `salary_currency`, `salary_period` | 薪资币种与周期 |
| `salary_min`, `salary_max`, `salary_avg` | 原周期数值薪资 |
| `salary_*_annual` | 按固定工时假设年薪化后的同币种薪资 |
| `salary_avg_usd_annual_winsorized` | 仅 USD 非异常记录的 P1/P99 缩尾值 |
| `experience_year_min/max` | 职级映射得到的经验区间代理 |
| `is_fresh_graduate` | 是否包含 Entry-level 的代理标记 |
| `description_clean/tokens` | 清洗文本与 jieba 分词结果 |
| `description_length/word_count` | 描述字符数和英文空格词数 |
| `description_structure_count` | 职责、要求、福利等结构提示词命中数 |
| `skills_normalized`, `skill_count` | 规范化技能和技能数量 |
| `broad_category` | 按固定关键词映射的宽类岗位类别 |
| `is_it_data_role` | 工程或数据科学岗位标记 |
| `quality_score/label/level` | 信息质量规则分、二分类标签和展示等级 |

## 5. 薪资与异常值

薪资周期统一采用 annual×1、monthly×12、weekly×52、daily×260、hourly×2080。这个换算只用于统计比较，未考虑奖金、股权、工时差异和税制。不同币种不做汇率换算。年薪化低于 5,000 或高于 1,000,000，以及上下限倒置的记录只打标，不删除；USD 分析值进一步按 P1/P99 缩尾。

## 6. 岗位信息质量标签

总分 100 分：追溯字段 5、核心字段 10、地点限制 5、描述完整性 25、薪资透明度 15、技能清晰度 20、职级 10、时效性 5、类别 5。描述长度和技能数采用分段递增并设上限，防止单一“是/否”字段决定标签。`quality_score >= 80` 定义为高信息质量。当前分布为 High 77、Medium 123、Low 0。

该标签是可复现的课程代理标签。它衡量岗位信息是否完整透明，不代表雇主信誉、工作体验、薪酬竞争力或候选人最终录用概率。后续应通过人工抽样标注或求职结果反馈建立外部效度。

## 7. 可复现命令

```bash
PYTHONPATH=src .venv/bin/python -m job_analysis.cleaning --sample-size 200
PYTHONPATH=src .venv/bin/python -m job_analysis.cleaning
```

样本命令只生成 `data/processed/sample_validation/` 下的验证结果；全量命令生成正式数据和报告。
