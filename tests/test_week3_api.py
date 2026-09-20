import io
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.backend import app


class Week3ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_reports_cleaned_dataset(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["data_records"], 12000)

    def test_match_text_enriches_quality_score(self):
        response = self.client.post(
            "/api/match",
            json={"resume_text": "Python SQL pandas data analysis", "top_k": 2},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["input_type"], "text")
        self.assertGreaterEqual(len(payload["results"]), 1)
        self.assertIn("quality_score", payload["results"][0])
        self.assertIn("source_url", payload["results"][0])

    def test_match_empty_text_is_rejected(self):
        response = self.client.post("/api/match", json={"resume_text": ""})
        self.assertEqual(response.status_code, 422)

    def test_match_whitespace_text_is_rejected(self):
        response = self.client.post("/api/match", json={"resume_text": "   \n\t"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("简历文本不能为空", response.json()["detail"])

    def test_match_top_k_boundary_values(self):
        lower = self.client.post(
            "/api/match", json={"resume_text": "Python SQL", "top_k": 1}
        )
        self.assertEqual(lower.status_code, 200)
        self.assertEqual(len(lower.json()["results"]), 1)

        upper = self.client.post(
            "/api/match", json={"resume_text": "Python SQL", "top_k": 20}
        )
        self.assertEqual(upper.status_code, 200)
        self.assertLessEqual(len(upper.json()["results"]), 20)

    def test_match_top_k_out_of_range_is_rejected(self):
        below = self.client.post(
            "/api/match", json={"resume_text": "Python", "top_k": 0}
        )
        above = self.client.post(
            "/api/match", json={"resume_text": "Python", "top_k": 21}
        )
        self.assertEqual(below.status_code, 422)
        self.assertEqual(above.status_code, 422)

    def test_score_validation_and_not_found(self):
        missing = self.client.post("/api/score", json={})
        self.assertEqual(missing.status_code, 400)
        unknown = self.client.post("/api/score", json={"job_id": "does-not-exist"})
        self.assertEqual(unknown.status_code, 404)

    def test_cluster_summary(self):
        response = self.client.post("/api/cluster", json={"cluster_id": 0})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["results"]["cluster_id"], 0)
        self.assertTrue(payload["results"]["business_name"])

    def test_local_agent_does_not_call_external_model(self):
        response = self.client.post(
            "/api/chat",
            json={"task": "找 Python 和 SQL 的远程数据岗位", "top_k": 2, "use_real_model": False},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["model_call"])
        self.assertEqual(payload["agent_mode"], "local_rule_router")

    def test_real_agent_error_is_not_silently_downgraded(self):
        with patch("app.backend.OpenAIJobAgent", side_effect=RuntimeError("gateway timeout")):
            response = self.client.post(
                "/api/chat",
                json={"task": "说明聚类结果", "use_real_model": True},
            )
        self.assertEqual(response.status_code, 502)
        self.assertIn("gpt-5.6-sol 调用未成功", response.json()["detail"])

    def test_txt_upload_uses_same_matching_pipeline(self):
        response = self.client.post(
            "/api/match/upload",
            files={"file": ("resume.txt", io.BytesIO(b"Python SQL data analyst"), "text/plain")},
            params={"top_k": 1, "preferred_locations": "United States"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["input_type"], "txt")
        self.assertEqual(response.json()["filename"], "resume.txt")
        self.assertIn("location_score", response.json()["results"][0])

    def test_empty_upload_is_rejected(self):
        response = self.client.post(
            "/api/match/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_top_k_out_of_range_is_rejected(self):
        response = self.client.post(
            "/api/match/upload",
            files={"file": ("resume.txt", io.BytesIO(b"Python"), "text/plain")},
            params={"top_k": 21},
        )
        self.assertEqual(response.status_code, 400)

    def test_unsupported_upload_type_is_rejected(self):
        response = self.client.post(
            "/api/match/upload",
            files={"file": ("resume.docx", io.BytesIO(b"Python"), "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
