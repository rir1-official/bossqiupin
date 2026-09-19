from typing import Any, Dict, Iterable, List


def get_path(value: Any, path: str, default: Any = "") -> Any:
    current = value
    if not path:
        return current
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part, default)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return default
    return current


def normalize_item(item: Dict[str, Any], field_map: Dict[str, str], source: str, fallback_city: str) -> Dict[str, Any]:
    record = {name: get_path(item, path) for name, path in field_map.items()}
    record["source"] = source
    record["city"] = record.get("city") or fallback_city
    for key, value in list(record.items()):
        if isinstance(value, list):
            record[key] = ",".join(str(v).strip() for v in value if str(v).strip())
        elif value is None:
            record[key] = ""
        else:
            record[key] = str(value).strip()
    return record


def extract_items(payload: Dict[str, Any], items_path: str) -> List[Dict[str, Any]]:
    items = get_path(payload, items_path, [])
    if not isinstance(items, list):
        raise ValueError(f"items_path 未指向列表: {items_path}")
    return [item for item in items if isinstance(item, dict)]

