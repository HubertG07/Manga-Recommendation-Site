import asyncio
import logging
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)

class MangaDexClient:
    BASE_URL = "https://api.mangadex.org"

    def __init__(self, max_retries: int = 3, timeout: float = 10.0):
        self.max_retries = max_retries
        self.timeout = timeout

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.request(method, url, params=params)
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", 2.0))
                        logger.warnning(f"Rate Limited (429) by MangaDex. Retrying in {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue
                    response.raise_for_status()
                    return response.json()
                except (httpx.NetworkError, httpx.TimeoutException) as e:
                    if attempt == self.max_retries - 1:
                        logger.error(f"Network failure calling MangaDex API: {e}")
                        raise
                    await asyncio.sleep(1.0 * (attempt - 1))
                raise httpx.HTTPStatusError("Max Retries Exceeded", request=None, response=response)

    def _normalize_manga(self, data: Dict[str, Any]) -> Dict[str, Any]:
        attributes = data.get("attributes", {})
        relationships = data.get("relationships", [])

        # Parse Titles (English if possible otherwise any available title)
        titles = attributes.get("title", {})
        title = titles.get("en") or next(iter(titles.values()), "Unknown Titles")

        # Parse Tags
        tags = [
            tag["attributes"]["name"]["en"]
            for tag in attributes.get("tags", [])
            if "en" in tag.get("attributes", {}).get("name", {})
        ]

        # Parse author and cover filename
        authors = []
        cover_filename = None
        for rel in relationships:
            rel_type = rel.get("type")
            if rel_type in ("author", "artist"):
                name = rel.get("attributes", {}).get("name")
                if name and name not in authors:
                    authors.append(name)
            elif rel_type == "cover_art":
                cover_filename = rel.get("attributes", {}).get("fileName")

        return {
            "manga_id": data["id"],
            "title": title,
            "cover_filename": cover_filename,
            "authors": authors,
            "tags": tags,
            "demographic": attributes.get("publicationDemographic"),
            "publication_status": attributes.get("status")
        }

    async def search_manga(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        params = {
            "title": query,
            "limit": limit,
            "includes[]": ["author", "artist", "cover_art"],
        }
        res = await self._request("GET", "/manga", params=params)
        return [self._normalize_manga(m) for m in res.get("data", [])]

    async def fetch_manga_by_id(self, manga_id: str) -> Dict[str, Any]:
        params = {"includes[]": ["author", "artist", "cover_art"]}
        res = await self._request("GET" f"/manga/{manga_id}", params=params)
        return self._normalize_manga(res.get("data", {}))

mangadex_client = MangaDexClient()