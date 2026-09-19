import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from job_analysis.cleaning import (
    clean_record,
    deduplicate_records,
    ensure_derived_output,
    parse_experience,
    parse_salary,
)


class CleaningTest(unittest.TestCase):
    def test_salary_parsing_and_annualization(self):
        parsed = parse_salary("USD 50-60 hourly")
        self.assertEqual(parsed["salary_min"], 50)
        self.assertEqual(parsed["salary_max"], 60)
        self.assertEqual(parsed["salary_avg_annual"], 114400)
        self.assertFalse(parsed["salary_outlier"])

    def test_salary_missing_stays_missing(self):
        parsed = parse_salary("")
        self.assertEqual(parsed["salary_parse_status"], "missing")
        self.assertIsNone(parsed["salary_avg"])

    def test_experience_proxy_mapping(self):
        parsed = parse_experience("Entry-level, Mid-level")
        self.assertEqual(parsed["experience_year_min"], 0)
        self.assertEqual(parsed["experience_year_max"], 5)
        self.assertTrue(parsed["is_fresh_graduate"])

    def test_dedupe_prefers_source_and_job_id(self):
        rows = [
            {"source": "himalayas_api", "job_id": "a", "source_url": "u1"},
            {"source": "himalayas_api", "job_id": "a", "source_url": "u2"},
        ]
        unique, duplicates = deduplicate_records(rows)
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["dedupe_key_type"], "source_job_id")

    def test_raw_output_is_rejected(self):
        with self.assertRaises(ValueError):
            ensure_derived_output(Path("data/raw/derived.jsonl"))

    def test_clean_record_keeps_traceability_and_remote(self):
        row = {
            "job_id": "a",
            "job_title": "Data Analyst",
            "company_name": "Example",
            "city": "Remote",
            "district": "United States",
            "salary_raw": "USD 80000-100000 annual",
            "experience_raw": "Mid-level",
            "publish_date": "2026-09-01T00:00:00+00:00",
            "job_description": "Responsibilities analyze data. Requirements SQL and Python. Benefits health insurance.",
            "skills": "Python, SQL, Analytics, Tableau, Statistics",
            "job_category": "Data Science",
            "source": "himalayas_api",
            "source_url": "https://example.test/job/a",
            "crawl_time": "2026-09-08T00:00:00+00:00",
            "data_origin": "authorized_api_collection",
        }
        cleaned = clean_record(row, datetime(2026, 9, 8, tzinfo=timezone.utc))
        self.assertEqual(cleaned["city"], "Remote")
        self.assertEqual(cleaned["source_url"], row["source_url"])
        self.assertEqual(cleaned["crawl_time"], row["crawl_time"])
        self.assertEqual(cleaned["data_origin"], row["data_origin"])
        self.assertEqual(cleaned["broad_category"], "Data Science")
        self.assertGreater(cleaned["skill_count"], 0)


if __name__ == "__main__":
    unittest.main()
