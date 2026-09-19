import json
import random
import time
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


USER_AGENTS = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
)


class AccessBlocked(RuntimeError):
    pass


class PublicHttpClient:
    def __init__(self, settings: Dict[str, Any], sleep=time.sleep, rng=random.uniform):
        self.settings = settings
        self.sleep = sleep
        self.rng = rng

    def _pause(self) -> None:
        self.sleep(self.rng(self.settings["min_delay_seconds"], self.settings["max_delay_seconds"]))

    def get_json_with_raw(self, url: str):
        retries = int(self.settings.get("max_retries", 3))
        for attempt in range(retries):
            self._pause()
            request = Request(url, headers={"User-Agent": random.choice(USER_AGENTS), "Accept": "application/json,text/plain,*/*"})
            try:
                with urlopen(request, timeout=self.settings.get("timeout_seconds", 20)) as response:
                    status = response.getcode()
                    payload = response.read().decode("utf-8", errors="replace")
                if status in (403, 429):
                    raise AccessBlocked(f"访问受限: HTTP {status}")
                lowered = payload.lower()
                if any(marker in lowered for marker in ("captcha", "验证码", "登录后", "请登录")):
                    raise AccessBlocked("页面要求登录或验证码")
                return json.loads(payload), payload
            except AccessBlocked:
                raise
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                if isinstance(exc, HTTPError) and exc.code in (403, 429):
                    raise AccessBlocked(f"访问受限: HTTP {exc.code}") from exc
                if attempt == retries - 1:
                    raise RuntimeError(f"请求失败: {url}: {exc}") from exc
                self.sleep(2 ** attempt)
        raise RuntimeError("不可达")

    def get_json(self, url: str) -> Dict[str, Any]:
        """Fetch a public JSON endpoint and discard the archival response body."""
        return self.get_json_with_raw(url)[0]


def render_url(template: str, city: str, keyword: str, page: int) -> str:
    return template.format(city=quote(city), keyword=quote(keyword), page=page)
