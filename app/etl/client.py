"""HTTP client for the source system, with paging and retries."""
import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class SourceClient:
    def __init__(self, base_url: str, page_size: int = 100, timeout: float = 10.0) -> None:
        self.page_size = page_size
        self._http = httpx.Client(base_url=base_url, timeout=timeout)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=8),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _get(self, path: str, params: dict) -> dict:
        response = self._http.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_all(self, resource: str, key: str) -> list[dict]:
        """Read every page of /<resource> and return the records under `key`."""
        items: list[dict] = []
        skip = 0
        while True:
            data = self._get(f"/{resource}", {"limit": self.page_size, "skip": skip})
            batch = data.get(key, [])
            items.extend(batch)
            skip += len(batch)
            logger.info("Fetched %s %s so far (%s)", len(items), resource, data.get("total"))
            if not batch or skip >= data.get("total", skip):
                break
        return items
