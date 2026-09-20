"""Capture reproducible Week 3 Docker smoke-test evidence.

The script talks only to the locally running frontend and API containers. It
stores response metadata and tool outputs, never environment variables or API
credentials.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports/week3/docker_smoke_20260920.json"
AGENT_DEMO_PATH = ROOT / "reports/agent/real_demo_output.json"


def request_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 180) -> tuple[dict[str, Any], float]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
        return body, round(time.perf_counter() - started, 3)


def frontend_status(url: str, timeout: int = 15) -> tuple[int, float]:
    started = time.perf_counter()
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.status, round(time.perf_counter() - started, 3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:8501")
    parser.add_argument(
        "--include-agent",
        action="store_true",
        help="Explicitly run the paid real-model Agent check; omitted by default.",
    )
    args = parser.parse_args()

    api = args.api_url.rstrip("/")
    evidence: dict[str, Any] = {
        "captured_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "scope": "Locally running Docker Compose services",
    }
    try:
        health, health_seconds = request_json(f"{api}/api/health")
        runtime, runtime_seconds = request_json(f"{api}/api/agent_runtime")
        retrieval, retrieval_seconds = request_json(
            f"{api}/api/retrieve",
            {"question": "Python SQL remote data analyst jobs", "top_k": 1},
        )
        status, frontend_seconds = frontend_status(args.frontend_url)
        evidence.update(
            {
                "health": {"elapsed_seconds": health_seconds, "response": health},
                "frontend": {"status_code": status, "elapsed_seconds": frontend_seconds},
                "agent_runtime": {"elapsed_seconds": runtime_seconds, "response": runtime},
                "retrieval": {
                    "elapsed_seconds": retrieval_seconds,
                    "method": retrieval.get("method"),
                    "embedding_model": retrieval.get("embedding_model"),
                    "results": retrieval.get("results", []),
                },
            }
        )
        if args.include_agent:
            agent, agent_seconds = request_json(
                f"{api}/api/chat",
                {
                    "task": "请调用 cluster_summary 工具，用两句话概括第0类岗位。",
                    "top_k": 3,
                    "use_real_model": True,
                },
            )
            evidence["real_agent"] = {"elapsed_seconds": agent_seconds, "response": agent}
            AGENT_DEMO_PATH.parent.mkdir(parents=True, exist_ok=True)
            AGENT_DEMO_PATH.write_text(json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8")
        evidence["passed"] = True
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        evidence["passed"] = False
        evidence["error"] = str(exc)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if not evidence.get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
