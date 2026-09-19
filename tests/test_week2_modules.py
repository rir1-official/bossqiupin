import tempfile
import unittest
from pathlib import Path

import pandas as pd

from job_analysis.agent import FUNCTION_SCHEMAS, LocalJobAgent
from job_analysis.clustering import build_cluster_text, evaluate_k_values, summarize_clusters
from job_analysis.rag_faiss import build_chunk_dataframe, parse_job_sections
from job_analysis.retrieval import JobRetriever, build_documents, normalize_query


def sample_jobs() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "job_id": "job-python",
                "job_title": "Python Data Analyst",
                "company_name": "Data Co",
                "broad_category": "Data Science",
                "job_category": "Data Analyst",
                "skills_normalized": "python | sql | tableau",
                "description_clean": "python sql tableau analytics",
                "district": "United States",
                "salary_raw": "USD 90000 annual",
                "source_url": "https://example.test/python",
                "crawl_time": "2026-09-08T00:00:00Z",
                "data_origin": "authorized_api_collection",
                "quality_score": 91,
                "quality_level": "High",
                "experience_year_min": 2,
                "experience_year_max": 5,
            },
            {
                "job_id": "job-java",
                "job_title": "Java Backend Engineer",
                "company_name": "Eng Co",
                "broad_category": "Engineering",
                "job_category": "Developer",
                "skills_normalized": "java | docker | kubernetes",
                "description_clean": "java backend docker kubernetes",
                "district": "Canada",
                "salary_raw": "",
                "source_url": "https://example.test/java",
                "crawl_time": "2026-09-08T00:00:00Z",
                "data_origin": "authorized_api_collection",
                "quality_score": 70,
                "quality_level": "Medium",
                "experience_year_min": 5,
                "experience_year_max": 10,
            },
            {
                "job_id": "job-marketing",
                "job_title": "Growth Marketing Manager",
                "company_name": "Market Co",
                "broad_category": "Marketing",
                "job_category": "Marketing",
                "skills_normalized": "seo | marketing",
                "description_clean": "growth marketing seo",
                "district": "United Kingdom",
                "salary_raw": "",
                "source_url": "https://example.test/marketing",
                "crawl_time": "2026-09-08T00:00:00Z",
                "data_origin": "authorized_api_collection",
                "quality_score": 65,
                "quality_level": "Medium",
                "experience_year_min": 2,
                "experience_year_max": 8,
            },
        ]
    )


class Week2ModulesTest(unittest.TestCase):
    def test_rag_sections_keep_explicit_headings_and_fallback(self):
        parsed = parse_job_sections(
            "About the Role: Build data products for an international remote analytics team. "
            "Responsibilities: Analyze experiments, write SQL queries, and document weekly findings. "
            "Requirements: Python, SQL and three years of relevant experience are required."
        )
        self.assertEqual(parsed["sources"]["job_introduction"], "explicit_heading")
        self.assertEqual(parsed["sources"]["responsibilities"], "explicit_heading")
        self.assertEqual(parsed["sources"]["requirements"], "explicit_heading")
        fallback = parse_job_sections("Build data products with Python and SQL for a remote team.")
        self.assertTrue(all(value == "full_description_fallback" for value in fallback["sources"].values()))

        jobs = sample_jobs().copy()
        jobs["rag_description"] = [
            "About the Role: Analyze data for an international remote analytics team. Responsibilities: Write SQL queries and document weekly findings. Requirements: Python and SQL experience are required.",
            "Build backend services with Java and Docker for a remote team.",
            "Grow demand through SEO and content marketing for a remote team.",
        ]
        sections = [parse_job_sections(text) for text in jobs["rag_description"]]
        jobs["job_introduction"] = [item["job_introduction"] for item in sections]
        jobs["responsibilities_text"] = [item["responsibilities"] for item in sections]
        jobs["requirements_text"] = [item["requirements"] for item in sections]
        jobs["section_parse_summary"] = [item["summary"] for item in sections]
        chunks = build_chunk_dataframe(jobs, chunk_size=200, overlap=20)
        self.assertIn("section_name", chunks.columns)
        self.assertTrue(any(chunks["section_name"] == "岗位职责"))
        self.assertTrue(any(chunks["section_name"] == "岗位综合文本（回退）"))
        self.assertTrue(chunks["chunk_id"].str.contains("::").all())

    def test_clustering_helpers_return_metrics_and_summary(self):
        jobs = sample_jobs()
        vectorizer_text = build_cluster_text(jobs)
        self.assertEqual(len(vectorizer_text), 3)
        from sklearn.feature_extraction.text import TfidfVectorizer

        matrix = TfidfVectorizer().fit_transform(vectorizer_text)
        metrics, fitted = evaluate_k_values(matrix, [2], silhouette_sample_size=3)
        self.assertEqual(set(metrics["k"]), {2})
        self.assertEqual(set(fitted), {2})
        summary = summarize_clusters(jobs, fitted[2].labels_, fitted[2], TfidfVectorizer().fit(vectorizer_text).get_feature_names_out())
        self.assertEqual(sum(item["job_count"] for item in summary), 3)
        self.assertTrue(all(item["business_name"] for item in summary))

    def test_retriever_returns_traceable_top_k(self):
        jobs = sample_jobs()
        retriever = JobRetriever().fit(jobs)
        self.assertIn("python", normalize_query("Python 岗位"))
        self.assertEqual(len(build_documents(jobs)), 3)
        result = retriever.search("Python SQL", top_k=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["job_id"], "job-python")
        self.assertEqual(result[0]["source_url"], "https://example.test/python")
        self.assertEqual(result[0]["data_origin"], "authorized_api_collection")

    def test_agent_schema_and_local_tools(self):
        jobs = sample_jobs()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data_path = tmp_path / "jobs.parquet"
            index_dir = tmp_path / "rag"
            jobs.to_parquet(data_path, index=False)
            JobRetriever().fit(jobs).save(index_dir)
            cluster_path = tmp_path / "cluster_summary.json"
            cluster_path.write_text('[{"cluster_id": 1, "business_name": "Data group", "job_count": 1}]', encoding="utf-8")
            semantic_rows = [
                {
                    "job_id": "job-python",
                    "skills_normalized": "python | sql | tableau",
                    "broad_category": "Data Science",
                    "district": "United States",
                }
            ]
            class FakeSemanticRetriever:
                def search(self, question, top_k=5):
                    return semantic_rows[:top_k]

            agent = LocalJobAgent(
                data_path, index_dir, cluster_path,
                semantic_retriever_loader=lambda: FakeSemanticRetriever(),
            )
            scored = agent.score_job(job_id="job-python")
            self.assertEqual(scored["quality_level"], "High")
            self.assertEqual(agent.retrieve_jobs("Python SQL", top_k=1)[0]["job_id"], "job-python")
            filtered = agent.retrieve_jobs("Python SQL", top_k=2, skills=["python"], category="Data Science", district="United States")
            self.assertEqual([item["job_id"] for item in filtered], ["job-python"])
            self.assertEqual(agent.cluster_summary(1)["business_name"], "Data group")
            routed = agent.run("帮我找 Python SQL 的美国远程数据岗位", top_k=1)
            self.assertEqual(routed["tool_calls"][0]["tool"], "match_resume")
            self.assertFalse(routed["model_call"])
            composite = agent.run("请匹配 Python SQL 简历，并说明哪些岗位信息质量较高", top_k=2)
            self.assertEqual(composite["tool_calls"][0]["tool"], "match_resume")
            self.assertTrue(any(call["tool"] == "score_job" for call in composite["tool_calls"]))
            self.assertFalse(composite["model_call"])
        self.assertEqual({schema["name"] for schema in FUNCTION_SCHEMAS}, {"search_jobs", "score_job", "match_resume", "cluster_summary", "retrieve_jobs"})

    def test_agent_never_falls_back_to_tfidf_for_rag(self):
        jobs = sample_jobs()
        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "jobs.parquet"
            jobs.to_parquet(data_path, index=False)
            agent = LocalJobAgent(
                data_path,
                Path(tmp) / "unused",
                Path(tmp) / "missing-clusters.json",
                semantic_retriever_loader=lambda: (_ for _ in ()).throw(RuntimeError("BGE unavailable")),
            )
            with self.assertRaises(RuntimeError):
                agent.retrieve_jobs("Python SQL", top_k=1)


if __name__ == "__main__":
    unittest.main()
