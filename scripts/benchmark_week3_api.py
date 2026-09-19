"""Measure cold initialization and warmed API matching latency for Week 3."""

from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/week3/api_test_timings_optimized.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.backend as backend


def timed_call(client: TestClient, path: str, payload: dict) -> tuple[int, float]:
    started = time.perf_counter()
    response = client.post(path, json=payload)
    elapsed = time.perf_counter() - started
    return response.status_code, elapsed


def main() -> None:
    backend._agent.cache_clear()
    backend._load_jobs.cache_clear()
    client = TestClient(backend.app)

    cold_status, cold_seconds = timed_call(
        client,
        "/api/match",
        {"resume_text": "Python SQL pandas data analysis", "top_k": 5},
    )

    cases = []
    for name, payload in (
        ("warm_match_top_k_5", {"resume_text": "Python SQL pandas data analysis", "top_k": 5}),
        ("warm_match_top_k_1", {"resume_text": "Python SQL", "top_k": 1}),
        ("warm_match_top_k_20", {"resume_text": "Python SQL", "top_k": 20}),
    ):
        statuses = []
        runs = []
        for _ in range(5):
            status, elapsed = timed_call(client, "/api/match", payload)
            statuses.append(status)
            runs.append(round(elapsed, 4))
        cases.append(
            {
                "case": name,
                "statuses": statuses,
                "runs_seconds": runs,
                "median_seconds": round(statistics.median(runs), 4),
            }
        )

    payload = {
        "generated_at": date.today().isoformat(),
        "measurement": "FastAPI TestClient on the local project Python runtime",
        "cold_initialization": {
            "status": cold_status,
            "seconds": round(cold_seconds, 4),
            "includes": "Parquet load, LocalJobAgent initialization, TF-IDF matching index construction, and first match",
        },
        "warm_cases": cases,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
