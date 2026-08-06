"""Agent registry — plug in new specialists without rewriting the router."""

from __future__ import annotations

from typing import Dict, List, Type

from app.agents.booking import BookingAgent
from app.agents.distributor import DistributorAgent
from app.agents.document import DocumentAgent
from app.agents.finance import FinanceAgent
from app.agents.investor import InvestorAgent
from app.agents.marketing import MarketingAgent
from app.agents.specialist_base import AgentInfo, SpecialistAgent
from app.agents.support import SupportAgent
from app.ai.service import AIService
from app.rag.retriever import Retriever

# Register new agents here only — AgentRouter discovers them automatically.
AGENT_CLASSES: List[Type[SpecialistAgent]] = [
    MarketingAgent,
    InvestorAgent,
    DistributorAgent,
    DocumentAgent,
    FinanceAgent,
    SupportAgent,
    BookingAgent,
]


def build_agent_registry(
    ai: AIService, retriever: Retriever
) -> Dict[str, SpecialistAgent]:
    return {cls.info.id: cls(ai, retriever) for cls in AGENT_CLASSES}


def catalog() -> List[dict]:
    return [
        {
            "id": cls.info.id,
            "name": cls.info.name,
            "title": cls.info.title,
            "description": cls.info.description,
            "skills": list(cls.info.skills),
            "status": cls.info.status,
            "icon": cls.info.icon,
        }
        for cls in AGENT_CLASSES
    ]


def get_info(agent_id: str) -> AgentInfo | None:
    for cls in AGENT_CLASSES:
        if cls.info.id == agent_id:
            return cls.info
    return None
