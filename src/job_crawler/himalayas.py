"""Cursor-based collection for the Himalayas public jobs API.

This module is enabled only after the project owner has obtained permission for
the intended academic collection. It never uses login state or bypasses access
controls.
"""

import hashlib
import html
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import JobRecord
from .storage import append_log, write_page, write_response


API_URL = "https://himalayas.app/jobs/api"
SOURCE_NAME = "himalayas_api"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(value: Any) -> str:
    parser = _TextExtractor()
    parser.feed(str(value or ""))
    return re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()


def as_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def epoch_to_iso(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return ""


def salary_text(item: Dict[str, Any]) -> str:
    minimum, maximum = item.get("minSalary"), item.get("maxSalary")
    currency, period = as_text(item.get("currency")), as_text(item.get("salaryPeriod"))
    if minimum is None and maximum is None:
        return ""
    if minimum is None:
        amount = f"up to {maximum}"
    elif maximum is None:
        amount = f"from {minimum}"
    else:
        amount = f"{minimum}-{maximum}"
    return " ".join(part for part in (currency, amount, period) if part)


def normalize_himalayas_job(item: Dict[str, Any], crawl_time: str) -> Dict[str, Any]:
    source_url = as_text(item.get("guid")) or as_text(item.get("applicationLink"))
    job_id = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:24] if source_url else ""
    locations = as_text(item.get("locationRestrictions"))
    record = JobRecord.from_dict(
        {
            "job_id": job_id,
            "job_title": as_text(item.get("title")),
            "company_name": as_text(item.get("companyName")),
            "city": "Remote",
            "district": locations,
            "salary_raw": salary_text(item),
            "experience_raw": as_text(item.get("seniority")),
            "publish_date": epoch_to_iso(item.get("pubDate")),
            "job_description": html_to_text(item.get("description")) or as_text(item.get("excerpt")),
            "skills": as_text(item.get("categories")),
            "job_category": as_text(item.get("parentCategories")) or as_text(item.get("categories")),
            "source": SOURCE_NAME,
            "source_url": source_url,
            "crawl_time": crawl_time,
            "data_origin": "authorized_api_collection",
        }
    )
    return record.to_dict()


def fetch_page(cursor: Optional[str] = None, timeout_seconds: int = 30) -> tuple[Dict[str, Any], str, str]:
    query = urlencode({"cursor": cursor}) if cursor else ""
    url = f"{API_URL}?{query}" if query else API_URL
    request = Request(
        url,
        headers={
            "User-Agent": "AcademicJobMarketResearch/1.0 (authorized collection)",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = response.getcode()
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"API returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc
    if status in (403, 429):
        raise RuntimeError(f"API access stopped: HTTP {status}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("API did not return JSON") from exc
    if not isinstance(payload.get("jobs"), list):
        raise RuntimeError("API response has no jobs list")
    return payload, raw, url


def load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"cursor": None, "page": 0, "records": 0}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def crawl_himalayas(
    target_records: int = 10000,
    delay_seconds: float = 1.0,
    raw_root: str = "data/raw",
    state_path: str = "logs/himalayas_state.json",
    timeout_seconds: int = 30,
) -> Dict[str, int]:
    """Collect up to target_records and persist progress after every API page."""
    if target_records < 1:
        raise ValueError("target_records must be positive")
    if delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative")

    state_file = Path(state_path)
    state = load_state(state_file)
    stats = {"pages_ok": 0, "records_written": 0, "records_total": int(state.get("records", 0))}
    while stats["records_total"] < target_records:
        page_number = int(state.get("page", 0)) + 1
        crawl_time = datetime.now(timezone.utc).isoformat()
        payload, raw, url = fetch_page(state.get("cursor"), timeout_seconds)
        jobs: Iterable[Dict[str, Any]] = payload["jobs"]
        records = [normalize_himalayas_job(item, crawl_time) for item in jobs if isinstance(item, dict)]
        if not records:
            break
        remaining = target_records - stats["records_total"]
        records = records[:remaining]
        write_response(raw, SOURCE_NAME, "remote", "all", page_number)
        write_page(records, SOURCE_NAME, "remote", "all", page_number, raw_root)
        stats["pages_ok"] += 1
        stats["records_written"] += len(records)
        stats["records_total"] += len(records)
        state = {"cursor": payload.get("nextCursor"), "page": page_number, "records": stats["records_total"], "updated_at": crawl_time}
        save_state(state_file, state)
        append_log({"time": crawl_time, "source": SOURCE_NAME, "city": "Remote", "keyword": "all", "page": page_number, "status": "ok", "records": len(records), "message": url})
        if not state["cursor"] or stats["records_total"] >= target_records:
            break
        time.sleep(delay_seconds)
    return stats
