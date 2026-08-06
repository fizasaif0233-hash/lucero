"""Research Agent — knowledge-first, then optional web search."""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import UUID

import httpx

from app.agents.base import AgentProgress, AgentResult, BaseAgent
from app.ai.service import AIService
from app.core.config import Settings, get_settings
from app.rag.retriever import RetrievedChunk, Retriever
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ResearchAgent(BaseAgent):
    """
    Research agent for investor / distributor / market discovery.

    1) Search internal Assets / RAG (primary)
    2) Optionally search the public web (Serper if configured, else DuckDuckGo)
    3) Return a context block for L.U.C.E.R.O to answer as a business partner
    """

    name = "research"

    def __init__(
        self,
        ai_service: AIService,
        retriever: Retriever,
        *,
        enable_web: bool = True,
        settings: Optional[Settings] = None,
    ) -> None:
        self._ai = ai_service
        self._retriever = retriever
        self._enable_web = enable_web
        self._settings = settings or get_settings()

    async def run(
        self,
        query: str,
        *,
        user_id: str | UUID,
        search_queries: tuple[str, ...] = (),
        **kwargs,
    ) -> AsyncIterator[AgentProgress | AgentResult]:
        queries = list(search_queries) or [query]

        yield AgentProgress("thinking", "Planning research approach…")
        yield AgentProgress(
            "knowledge", "Searching your business documents and Assets…"
        )

        rag_chunks: List[RetrievedChunk] = []
        seen_ids = set()
        for q in queries:
            hits = await self._retriever.retrieve(
                q, user_id, top_k=8, threshold=0.30
            )
            for hit in hits:
                if hit.id in seen_ids:
                    continue
                seen_ids.add(hit.id)
                rag_chunks.append(hit)
            if len(rag_chunks) >= 10:
                break

        yield AgentProgress(
            "knowledge_done",
            f"Found {len(rag_chunks)} relevant internal document excerpts",
        )

        web_results: List[Dict[str, Any]] = []
        if self._enable_web:
            yield AgentProgress("web", "Searching the web for additional leads…")
            web_results = await self._web_search(queries[:3])
            if web_results:
                yield AgentProgress(
                    "web_done", f"Found {len(web_results)} web results"
                )
            else:
                yield AgentProgress(
                    "web_done",
                    "Web search unavailable or empty — using internal Assets",
                )
        else:
            yield AgentProgress("web_skipped", "Web research disabled")

        yield AgentProgress("report", "Compiling ranked research report…")

        context = self._build_context(query, rag_chunks, web_results)
        summary = (
            f"Internal docs: {len(rag_chunks)} excerpts. "
            f"Web results: {len(web_results)}."
        )
        sources = [
            {
                "type": "document",
                "id": c.id,
                "preview": c.content[:160],
                "similarity": c.similarity,
            }
            for c in rag_chunks[:8]
        ] + [
            {
                "type": "web",
                "title": w.get("title"),
                "url": w.get("href") or w.get("url"),
                "preview": w.get("body") or w.get("snippet"),
            }
            for w in web_results[:8]
        ]

        yield AgentResult(summary=summary, sources=sources, context_block=context)

    async def _web_search(self, queries: List[str]) -> List[Dict[str, Any]]:
        if self._settings.serper_api_key:
            results = await self._serper_search(queries)
            if results:
                return results

        return await self._duckduckgo_search(queries)

    async def _serper_search(self, queries: List[str]) -> List[Dict[str, Any]]:
        key = self._settings.serper_api_key
        if not key:
            return []
        results: List[Dict[str, Any]] = []
        seen = set()
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                for q in queries:
                    resp = await client.post(
                        "https://google.serper.dev/search",
                        headers={
                            "X-API-KEY": key,
                            "Content-Type": "application/json",
                        },
                        json={"q": q, "num": 5},
                    )
                    if resp.status_code != 200:
                        logger.warning(
                            "serper_failed", status=resp.status_code, query=q
                        )
                        continue
                    data = resp.json()
                    for item in data.get("organic") or []:
                        url = item.get("link") or ""
                        if not url or url in seen:
                            continue
                        seen.add(url)
                        results.append(
                            {
                                "title": item.get("title") or "",
                                "href": url,
                                "body": item.get("snippet") or "",
                            }
                        )
                        if len(results) >= 12:
                            return results
        except Exception as exc:
            logger.warning("serper_error", error=str(exc))
        return results

    async def _duckduckgo_search(
        self, queries: List[str]
    ) -> List[Dict[str, Any]]:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.warning("duckduckgo_search_missing")
            return []

        results: List[Dict[str, Any]] = []
        seen = set()
        try:
            with DDGS() as ddgs:
                for q in queries:
                    try:
                        items = list(ddgs.text(q, max_results=5))
                    except Exception as exc:
                        logger.warning("ddg_query_failed", query=q, error=str(exc))
                        continue
                    for item in items:
                        url = item.get("href") or item.get("link") or ""
                        if not url or url in seen:
                            continue
                        seen.add(url)
                        results.append(
                            {
                                "title": item.get("title") or "",
                                "href": url,
                                "body": item.get("body")
                                or item.get("snippet")
                                or "",
                            }
                        )
                        if len(results) >= 12:
                            return results
        except Exception as exc:
            logger.warning("web_search_failed", error=str(exc))
        return results

    @staticmethod
    def _build_context(
        query: str,
        chunks: List[RetrievedChunk],
        web_results: List[Dict[str, Any]],
    ) -> str:
        parts = [
            f"Research request: {query}",
            "",
            "Instructions for L.U.C.E.R.O:",
            "- Act as Anthony's AI business partner executing research — not a coach.",
            "- Prefer concrete names, companies, segments, and next actions from sources.",
            "- Separate INTERNAL knowledge (Assets/documents) from EXTERNAL web findings "
            "and from GENERAL knowledge when you fill gaps.",
            "- Never refuse because internal documents are empty; use web + reasoning.",
            "- Do not invent private contact emails that are not present.",
            "- If internal Assets list crypto-luxury buyer segments, BlockBar, clubs,",
            "  distributors, or celebrity targets, present those as ranked leads/targets.",
            "",
        ]

        if chunks:
            parts.append("## Internal knowledge (Assets / documents)")
            for i, chunk in enumerate(chunks[:10], start=1):
                parts.append(
                    f"[Internal {i} | score={chunk.similarity:.2f}]\n{chunk.content}"
                )
                parts.append("---")
        else:
            parts.append(
                "## Internal knowledge\n"
                "No strong document matches. Continue with web findings and general knowledge."
            )

        if web_results:
            parts.append("## External web findings")
            for i, item in enumerate(web_results[:10], start=1):
                parts.append(
                    f"[Web {i}] {item.get('title')}\n"
                    f"URL: {item.get('href')}\n"
                    f"{item.get('body')}"
                )
                parts.append("---")
        else:
            parts.append(
                "## External web findings\n"
                "No live web results this turn. Answer fully from Internal knowledge "
                "and/or general knowledge — do not refuse."
            )

        return "\n".join(parts)
