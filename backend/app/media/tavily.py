"""Tavily web search client."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.core.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def tavily_search(
    query: str,
    *,
    settings: Optional[Settings] = None,
    max_results: int = 6,
) -> List[Dict[str, Any]]:
    cfg = settings or get_settings()
    key = (cfg.tavily_api_key or "").strip()
    if not key:
        return []
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": key,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": True,
                    "max_results": max_results,
                },
            )
            if resp.status_code >= 400:
                logger.warning("tavily_failed", status=resp.status_code)
                return []
            data = resp.json()
    except Exception as exc:
        logger.warning("tavily_error", error=str(exc))
        return []

    results: List[Dict[str, Any]] = []
    answer = data.get("answer")
    if answer:
        results.append(
            {
                "title": "Tavily summary",
                "href": "",
                "body": answer,
                "source": "tavily",
            }
        )
    for item in data.get("results") or []:
        results.append(
            {
                "title": item.get("title") or "",
                "href": item.get("url") or "",
                "body": item.get("content") or item.get("snippet") or "",
                "source": "tavily",
            }
        )
    return results
