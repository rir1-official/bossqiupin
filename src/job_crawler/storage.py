import csv
import json
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List


LOG_COLUMNS = ("time", "source", "city", "keyword", "page", "status", "records", "message")


def write_page(records: Iterable[Dict], source: str, city: str, keyword: str, page: int, root: str = "data/raw") -> Path:
    target = Path(root) / source / date.today().isoformat()
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{city}_{keyword}_{page}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def write_response(payload: str, source: str, city: str, keyword: str, page: int, root: str = "data/raw_responses") -> Path:
    """Archive public API responses separately from normalized JSONL records."""
    target = Path(root) / source / date.today().isoformat()
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{city}_{keyword}_{page}.json"
    path.write_text(payload, encoding="utf-8")
    return path


def append_log(row: Dict[str, object], path: str = "logs/crawl_log.csv") -> None:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    has_header = log_path.exists() and log_path.stat().st_size > 0
    with log_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_COLUMNS)
        if not has_header:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in LOG_COLUMNS})


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)
