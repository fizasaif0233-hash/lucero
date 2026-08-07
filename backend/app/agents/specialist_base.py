"""Shared contracts for L.U.C.E.R.O specialist agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.ai.service import AIService
from app.rag.retriever import Retriever


@dataclass(frozen=True)
class AgentInfo:
    id: str
    name: str
    title: str
    description: str
    skills: tuple[str, ...]
    status: str = "ready"
    icon: str = "bot"


@dataclass
class AgentContext:
    """Knowledge + instructions an agent contributes for a turn."""

    agent_id: str
    agent_name: str
    knowledge: str = ""
    instructions: str = ""
    search_queries: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentSection:
    agent_id: str
    agent_name: str
    content: str


class SpecialistAgent(ABC):
    """Independent specialist module — new agents register without changing the router core."""

    info: AgentInfo

    def __init__(self, ai: AIService, retriever: Retriever) -> None:
        self._ai = ai
        self._retriever = retriever

    @abstractmethod
    def relevance(self, message: str) -> float:
        """0–1 score for whether this agent should handle the message."""
        raise NotImplementedError

    @abstractmethod
    def knowledge_queries(self, message: str) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def role_instructions(self) -> str:
        raise NotImplementedError

    async def analyze(self, message: str) -> Dict[str, Any]:
        score = self.relevance(message)
        return {
            "agent_id": self.info.id,
            "score": score,
            "selected": score >= 0.45,
            "queries": self.knowledge_queries(message),
        }

    async def gather_context(
        self, *, user_id: str | UUID, message: str
    ) -> AgentContext:
        from app.rag.retriever import Retriever

        queries = self.knowledge_queries(message)
        hits_all = []
        seen = set()
        for q in queries[:4]:
            hits = await self._retriever.retrieve(
                q, user_id, top_k=6, threshold=0.28
            )
            for h in hits:
                if h.id in seen:
                    continue
                seen.add(h.id)
                hits_all.append(h)
            if len(hits_all) >= 8:
                break
        knowledge = Retriever.format_context(hits_all[:8])
        return AgentContext(
            agent_id=self.info.id,
            agent_name=self.info.name,
            knowledge=knowledge,
            instructions=self.role_instructions(),
            search_queries=queries,
            metadata={
                "rag_chunks": len(hits_all),
                "sources": [
                    {
                        "document_name": h.document_name,
                        "section": h.section,
                        "similarity": h.similarity,
                    }
                    for h in hits_all[:8]
                ],
            },
        )

    async def generate(
        self, *, message: str, context: AgentContext, history: Optional[str] = None
    ) -> AgentSection:
        prompt = (
            f"{context.instructions}\n\n"
            f"User request:\n{message}\n\n"
            f"Knowledge base excerpts:\n{context.knowledge or '(none)'}\n"
        )
        if history:
            prompt += f"\nRecent conversation:\n{history[-3000:]}"
        content = await self._ai.complete_task(
            f"You are the {context.agent_name}, part of L.U.C.E.R.O — ACTION-first. "
            "Open with a ✅ status line, then the finished package. "
            "No 'Here's…' / 'Feel free…' / 'You can adjust…' fluff. "
            "Assume Blue Prince21 McKinzy / 759 sticky brand defaults. "
            "Ask at most ONE clarifying question and only if blocked. Never return outlines unless asked. "
            "Prefer knowledge excerpts when relevant; otherwise use general expertise. Markdown.",
            prompt,
            temperature=0.55,
        )
        return AgentSection(
            agent_id=context.agent_id,
            agent_name=context.agent_name,
            content=content.strip(),
        )

    async def summarize(self, text: str) -> str:
        return await self._ai.complete_task(
            f"You are the {self.info.name}. Summarize concisely.",
            text[:12000],
            temperature=0.2,
        )

    async def execute(
        self, *, user_id: str | UUID, message: str
    ) -> AgentSection:
        ctx = await self.gather_context(user_id=user_id, message=message)
        return await self.generate(message=message, context=ctx)
