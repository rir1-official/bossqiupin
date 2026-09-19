from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict


REQUIRED_FIELDS = ("job_title", "company_name", "city", "source", "source_url", "crawl_time")


@dataclass
class JobRecord:
    job_id: str = ""
    job_title: str = ""
    company_name: str = ""
    city: str = ""
    district: str = ""
    salary_raw: str = ""
    experience_raw: str = ""
    education: str = ""
    publish_date: str = ""
    job_description: str = ""
    industry: str = ""
    company_type: str = ""
    company_size: str = ""
    skills: Any = ""
    job_category: str = ""
    longitude: str = ""
    latitude: str = ""
    source: str = ""
    source_url: str = ""
    crawl_time: str = ""
    data_origin: str = "self_crawled"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: Dict[str, Any]) -> "JobRecord":
        allowed = {name: values.get(name, "") for name in cls.__dataclass_fields__}
        if not allowed.get("crawl_time"):
            allowed["crawl_time"] = datetime.now(timezone.utc).isoformat()
        return cls(**allowed)

    def is_valid(self) -> bool:
        return all(str(getattr(self, field, "")).strip() for field in REQUIRED_FIELDS)

