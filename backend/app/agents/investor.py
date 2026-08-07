"""Investor Agent — fundraising, pipeline, outreach."""

from __future__ import annotations

import re
from typing import List

from app.agents.specialist_base import AgentInfo, SpecialistAgent


class InvestorAgent(SpecialistAgent):
    info = AgentInfo(
        id="investor",
        name="Investor Agent",
        title="Investor Agent",
        description="Raise capital with investor research, pipelines, pitch summaries, and outreach drafts.",
        skills=(
            "Investor research",
            "Pipeline organization",
            "Pitch summaries",
            "Outreach emails",
            "Fundraising strategy",
            "Investment opportunity analysis",
        ),
        icon="coins",
    )

    _PATTERNS = (
        r"\binvestor",
        r"\braise capital\b",
        r"\bfundrais",
        r"\bpitch (deck|summary)\b",
        r"\bventure capital\b|\bvc\b",
        r"\bangel investor",
        r"\binvestment opportunit",
        r"\bwho.*(invest|funding)",
        r"\bcapital (raise|needed|raise)\b",
        r"\bbusiness plan\b",
        r"\bswot\b",
        r"\bexit strateg",
    )

    def relevance(self, message: str) -> float:
        lower = message.lower()
        hits = sum(1 for p in self._PATTERNS if re.search(p, lower))
        if "investor" in lower or "investors" in lower:
            return 0.95
        if hits:
            return min(0.9, 0.55 + 0.15 * hits)
        return 0.05

    def knowledge_queries(self, message: str) -> List[str]:
        return [
            message,
            "tequila crypto investors BlockBar NFT luxury spirits collectors",
            "pitch deck fundraising capital token ecosystem",
            "celebrity influencer partner research investors",
            "Global Target Research crypto whale buyer segments",
        ]

    def role_instructions(self) -> str:
        return (
            "You are L.U.C.E.R.O Investor Agent. Help Anthony raise capital. "
            "Use uploaded documents/Assets first when relevant and label them. "
            "If docs are thin, continue with general fundraising expertise and any web research context. "
            "Never refuse because something is missing from uploads. "
            "Never invent private contact emails not present in sources. "
            "Deliver ranked pipelines, complete outreach emails, pitch summaries, and next steps — "
            "not outlines unless asked. For business plans deliver the full ACTION package: "
            "Exec Summary, Offer, Market, SWOT, Revenue Model, Marketing, Ops, Financial Forecast, "
            "KPIs, Risks, Timeline, Exit — default Blue Prince21 / 759. "
            "Open with ✅ Business plan ready. No fluff. ACTION mode: finish now; max 0–2 questions."
        )
