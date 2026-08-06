from html.parser import HTMLParser
from typing import Iterable, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx

from app.utils.logging import get_logger

logger = get_logger(__name__)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: List[str] = []
        self._skip = False
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip = True
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = " ".join(data.split())
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        return "\n".join(self._chunks)


class WebsiteCrawler:
    """
    Lightweight same-origin crawler for brand/knowledge sites.

    Designed for Phase 1 seeding. A future marketing/research agent can
    replace or extend this without changing chat/RAG APIs.
    """

    def __init__(
        self,
        *,
        max_pages: int = 25,
        timeout: float = 30.0,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
    ) -> None:
        self.max_pages = max_pages
        self.timeout = timeout
        self.user_agent = user_agent

    async def crawl(self, seed_urls: Iterable[str]) -> List[dict]:
        pages: List[dict] = []
        seen: Set[str] = set()
        queue: List[str] = []

        for seed in seed_urls:
            normalized = self._normalize(seed)
            if normalized and normalized not in seen:
                seen.add(normalized)
                queue.append(normalized)

        allowed_hosts = {urlparse(u).netloc.lower() for u in queue}

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent},
        ) as client:
            while queue and len(pages) < self.max_pages:
                url = queue.pop(0)
                try:
                    response = await client.get(url)
                    if response.status_code >= 400:
                        logger.warning(
                            "crawl_http_error", url=url, status=response.status_code
                        )
                        continue
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type and "text/plain" not in content_type:
                        continue

                    parser = _TextExtractor()
                    parser.feed(response.text)
                    text = parser.text().strip()
                    if len(text) < 80:
                        continue

                    pages.append(
                        {
                            "url": str(response.url),
                            "title": self._guess_title(text),
                            "content": text,
                        }
                    )

                    host = urlparse(str(response.url)).netloc.lower()
                    if host not in allowed_hosts:
                        continue

                    for href in parser.links:
                        absolute = self._normalize(urljoin(str(response.url), href))
                        if not absolute:
                            continue
                        if urlparse(absolute).netloc.lower() not in allowed_hosts:
                            continue
                        if absolute in seen:
                            continue
                        seen.add(absolute)
                        queue.append(absolute)
                except Exception as exc:
                    logger.warning("crawl_failed", url=url, error=str(exc))

        logger.info("crawl_complete", pages=len(pages), seeds=list(seed_urls))
        return pages

    @staticmethod
    def _normalize(url: str) -> Optional[str]:
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"}:
            return None
        # Drop fragments and common non-content paths
        path = parsed.path or "/"
        if any(
            path.lower().endswith(ext)
            for ext in (
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".webp",
                ".svg",
                ".css",
                ".js",
                ".ico",
                ".pdf",
                ".zip",
            )
        ):
            return None
        clean = f"{parsed.scheme}://{parsed.netloc.lower()}{path}"
        if parsed.query:
            clean = f"{clean}?{parsed.query}"
        if clean.endswith("/") and path != "/":
            clean = clean[:-1]
        return clean

    @staticmethod
    def _guess_title(text: str) -> str:
        first = text.split("\n", 1)[0].strip()
        return (first[:120] or "Untitled page")
