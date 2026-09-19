import json
from pathlib import Path
from typing import Any, Dict


def load_config(path: str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"request", "targets", "sources"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"配置缺少字段: {', '.join(sorted(missing))}")
    if not isinstance(data["sources"], list):
        raise ValueError("sources 必须是列表")
    return data

