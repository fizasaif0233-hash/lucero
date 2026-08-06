"""Distributor Agent — CRM, ranking, partnership outreach."""

from __future__ import annotations

import re
from typing import List

from app.agents.specialist_base import AgentInfo, SpecialistAgent
from app.automation.crm_data import contacts_as_text, load_crm_contacts


class DistributorAgent(SpecialistAgent):
    info = AgentInfo(
        id="distributor",
        name="Distributor Agent",
        title="Distributor Agent",
        description="Manage distributor relationships, CRM ranking, follow-ups, and distribution strategy.",
        skills=(
            "Distributor research",
            "CRM analysis & ranking",
            "Follow-up emails",
            "Partnership recommendations",
            "Distribution strategy",
            "Who to contact first",
        ),
        icon="handshake",
    )

    _PATTERNS = (
        r"\bdistributor",
        r"\bimporter\b",
        r"\bcrm\b",
        r"\bdubai\b.+\b(target|contact|distributor)",
        r"\bwho should i contact",
        r"\bfollow[- ]?up",
        r"\bpartnership\b",
        r"\bwholesale\b",
        r"\bfoley\b|\bafrican.?eastern\b",
    )

    def relevance(self, message: str) -> float:
        lower = message.lower()
        if re.search(r"\bdistributor", lower) or "who should i contact" in lower:
            return 0.95
        hits = sum(1 for p in self._PATTERNS if re.search(p, lower))
        return min(0.9, 0.5 + 0.15 * hits) if hits else 0.05

    def knowledge_queries(self, message: str) -> List[str]:
        return [
            message,
            "priority distributor research Dubai Tokyo London",
            "CRM Database 759 Targets Foley African Eastern",
            "distributor follow-up emails",
        ]

    def role_instructions(self) -> str:
        return (
            "You are L.U.C.E.R.O Distributor Agent. Prioritize HOT/HIGH CRM targets, "
            "rank who to contact first, and recommend concrete next actions. "
            "Use company names and intel from knowledge/CRM when available and label that source. "
            "If CRM/docs lack an answer, continue with distribution strategy from general knowledge "
            "and any web research — do not refuse. Do not invent email addresses."
        )

    async def gather_context(self, *, user_id, message: str):
        ctx = await super().gather_context(user_id=user_id, message=message)
        contacts = load_crm_contacts(limit=30)
        crm_block = contacts_as_text(contacts, limit=20)
        if crm_block and "No CRM" not in crm_block:
            ctx.knowledge = (
                f"## CRM contacts\n{crm_block}\n\n## Document knowledge\n{ctx.knowledge}"
            )
        return ctx
