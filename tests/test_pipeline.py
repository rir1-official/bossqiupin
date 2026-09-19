import json
import tempfile
import unittest
from pathlib import Path

from job_crawler.extract import extract_items, normalize_item
from job_crawler.himalayas import normalize_himalayas_job
from job_crawler.pipeline import dedupe_key, merge_and_dedupe, quality_summary


class PipelineTest(unittest.TestCase):
    def test_normalize_himalayas_job(self):
        job = {
            "title": "Backend Engineer",
            "companyName": "Example Inc.",
            "minSalary": 90000,
            "maxSalary": 120000,
            "currency": "USD",
            "salaryPeriod": "annual",
            "seniority": ["Mid-level"],
            "locationRestrictions": ["United States", "Canada"],
            "categories": ["Python", "Backend"],
            "description": "<p>Build <b>APIs</b> with Python.</p>",
            "pubDate": 1704067200,
            "guid": "https://himalayas.app/jobs/example",
        }
        record = normalize_himalayas_job(job, "2026-09-08T00:00:00+00:00")
        self.assertEqual(record["city"], "Remote")
        self.assertEqual(record["district"], "United States, Canada")
        self.assertEqual(record["salary_raw"], "USD 90000-120000 annual")
        self.assertEqual(record["job_description"], "Build APIs with Python.")
        self.assertEqual(record["source"], "himalayas_api")
        self.assertTrue(record["job_id"])

    def test_extract_nested_json_and_normalize(self):
        payload = {"data": {"items": [{"id": 8, "company": {"name": "示例公司"}, "skills": ["Python", "SQL"]}]}}
        item = extract_items(payload, "data.items")[0]
        record = normalize_item(item, {"job_id": "id", "company_name": "company.name", "skills": "skills"}, "sample", "厦门")
        self.assertEqual(record["job_id"], "8")
        self.assertEqual(record["company_name"], "示例公司")
        self.assertEqual(record["skills"], "Python,SQL")
        self.assertEqual(record["city"], "厦门")

    def test_merge_dedupes_job_id_then_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw" / "source" / "2026-09-08"
            raw.mkdir(parents=True)
            rows = [
                {"source": "source", "job_id": "1", "job_title": "Python", "company_name": "A", "city": "厦门", "source_url": "u", "crawl_time": "t"},
                {"source": "source", "job_id": "1", "job_title": "Python", "company_name": "A", "city": "厦门", "source_url": "u", "crawl_time": "t"},
                {"source": "source", "job_title": "Java", "company_name": "B", "city": "福州", "salary_raw": "10k", "publish_date": "2026-01-01", "source_url": "u2", "crawl_time": "t"},
            ]
            (raw / "page.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            result = merge_and_dedupe(str(Path(directory) / "raw"), str(Path(directory) / "merged.jsonl"))
            self.assertEqual(result, {"raw_records": 3, "deduped_records": 2, "duplicates": 1})

    def test_quality_measures_required_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.jsonl"
            row = {"job_title": "数据分析师", "company_name": "A", "city": "厦门", "source": "s", "source_url": "url", "crawl_time": "t", "salary_raw": "8-12K"}
            path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            summary = quality_summary(str(path))
            self.assertEqual(summary["total"], 1)
            self.assertEqual(summary["completeness"]["job_title"], 1)
            self.assertEqual(summary["salary_or_description"], 1)
