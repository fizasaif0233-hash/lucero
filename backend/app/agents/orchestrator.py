"""Orchestrates specialist agents for chat turns."""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import UUID

from app.agents.registry import build_agent_registry, catalog
from app.agents.specialist_base import AgentSection, SpecialistAgent
from app.agents.specialist_router import AgentRoute, AgentRouter
from app.ai.service import AIService
from app.rag.retriever import Retriever
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AgentOrchestrator:
    def __init__(self, ai: AIService, retriever: Retriever) -> None:
        self._ai = ai
        self._retriever = retriever
        self._agents = build_agent_registry(ai, retriever)
        self._router = AgentRouter(self._agents)

    def catalog(self) -> List[dict]:
        return catalog()

    def get(self, agent_id: str) -> Optional[SpecialistAgent]:
        return self._agents.get(agent_id)

    def route(
        self, message: str, *, forced_agent_id: Optional[str] = None
    ) -> AgentRoute:
        return self._router.route(message, forced_agent_id=forced_agent_id)

    async def run_turn(
        self,
        *,
        user_id: str | UUID,
        message: str,
        forced_agent_id: Optional[str] = None,
        memory_block: str = "",
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Yields progress dicts and a final payload:
          {"type":"route", ...}
          {"type":"progress", "agent_id", "agent_name", "detail"}
          {"type":"section", "agent_id", "agent_name", "content"}  (multi only)
          {"type":"context", "knowledge", "agents", "collaborative"}
        """
        route = self.route(message, forced_agent_id=forced_agent_id)
        agents_meta = self._router.describe(route.agent_ids)
        yield {
            "type": "route",
            "agents": agents_meta,
            "reason": route.reason,
            "collaborative": route.collaborative,
            "scores": route.scores,
        }

        sections: List[AgentSection] = []
        knowledge_parts: List[str] = []
        instruction_parts: List[str] = []

        for agent_id in route.agent_ids:
            agent = self._agents[agent_id]
            yield {
                "type": "progress",
                "agent_id": agent.info.id,
                "agent_name": agent.info.name,
                "detail": f"{agent.info.name} thinking…",
            }
            ctx = await agent.gather_context(user_id=user_id, message=message)
            if ctx.knowledge:
                knowledge_parts.append(
                    f"## {agent.info.name} knowledge\n{ctx.knowledge}"
                )
            instruction_parts.append(
                f"### {agent.info.name}\n{ctx.instructions}"
            )

            if route.collaborative:
                yield {
                    "type": "progress",
                    "agent_id": agent.info.id,
                    "agent_name": agent.info.name,
                    "detail": f"{agent.info.name} drafting section…",
                }
                section = await agent.generate(message=message, context=ctx)
                sections.append(section)
                yield {
                    "type": "section",
                    "agent_id": section.agent_id,
                    "agent_name": section.agent_name,
                    "content": section.content,
                }

        # General turn (no specialist): still search RAG, then Lucero answers freely.
        if not route.agent_ids:
            yield {
                "type": "progress",
                "agent_id": "lucero",
                "agent_name": "L.U.C.E.R.O",
                "detail": "Searching your documents, then answering…",
            }
            try:
                hits = await self._retriever.retrieve(
                    message, user_id, top_k=8, threshold=0.30
                )
                if hits:
                    from app.rag.retriever import Retriever

                    knowledge_parts.append(
                        "## Uploaded documents / Assets\n"
                        + Retriever.format_context(hits)
                    )
            except Exception:
                logger.exception("general_rag_retrieve_failed")
            instruction_parts.append(
                "### L.U.C.E.R.O general assistant\n"
                "Answer as L.U.C.E.R.O. Prefer uploaded document excerpts when relevant "
                "and cite them. If they do not cover the question, answer with general "
                "knowledge and label the source. Never refuse because uploads lack the answer."
            )

        knowledge = "\n\n".join(knowledge_parts)
        if memory_block:
            knowledge = f"{knowledge}\n\n## Business memory\n{memory_block}".strip()

        if route.collaborative and sections:
            merged_sections = "\n\n".join(
                f"## {s.agent_name}\n{s.content}" for s in sections
            )
            knowledge = (
                f"{knowledge}\n\n## Specialist drafts to merge\n{merged_sections}"
            ).strip()
            instruction_parts.append(
                "Multiple specialists contributed drafts above. "
                "Produce a Final Combined Report that merges them without losing key facts. "
                "Show clear sections per specialty, then an overall recommendation."
            )

        yield {
            "type": "context",
            "knowledge": knowledge,
            "instructions": "\n\n".join(instruction_parts),
            "agents": agents_meta,
            "collaborative": route.collaborative,
            "primary_agent": agents_meta[0] if agents_meta else None,
        }

    def build_system_overlay(self, instructions: str, agents: List[dict]) -> str:
        if not agents:
            return (
                "Active mode: General L.U.C.E.R.O assistant.\n"
                "Answer normally with document context when relevant, otherwise general knowledge.\n"
                f"{instructions}"
            )
        names = ", ".join(a["name"] for a in agents)
        collab = len(agents) > 1
        return (
            f"Active specialist agent(s): {names}.\n"
            f"{'Collaborative multi-agent mode.' if collab else 'Single-agent mode.'}\n"
            "Identify yourself as L.U.C.E.R.O speaking through these specialists when useful.\n"
            f"{instructions}"
        )
