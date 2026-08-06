"""Marketing Agent — campaigns, social, brand growth."""

from __future__ import annotations

import re
from typing import List

from app.agents.specialist_base import AgentInfo, SpecialistAgent


class MarketingAgent(SpecialistAgent):
    info = AgentInfo(
        id="marketing",
        name="Marketing Agent",
        title="Marketing Agent",
        description="Grow the business with campaigns, social posts, blogs, commercials, and brand strategy.",
        skills=(
            "30-day campaigns",
            "Instagram / Facebook / LinkedIn / X posts",
            "Blog articles & email campaigns",
            "Commercial & video scripts",
            "Hashtags & content calendars",
            "Brand strategy",
        ),
        icon="megaphone",
    )

    _PATTERNS = (
        r"\bmarketing\b",
        r"\bcampaign\b",
        r"\binstagram\b",
        r"\bfacebook\b",
        r"\blinkedin\b",
        r"\btwitter\b|\b\bx\b\s+post",
        r"\bhashtag",
        r"\bcontent calendar\b",
        r"\bcommercial\b",
        r"\bvideo (script|idea)",
        r"\bbrand strateg",
        r"\bcaption",
        r"\bad(vertisement)?\b",
        r"\bsocial media\b",
        r"\bnewsletter\b",
        r"\bblog\b",
    )

    def relevance(self, message: str) -> float:
        lower = message.lower()
        hits = sum(1 for p in self._PATTERNS if re.search(p, lower))
        if hits >= 2:
            return 0.95
        if hits == 1:
            return 0.8
        if re.search(r"\b(create|write|generate|draft)\b.+\b(post|email|script)\b", lower):
            return 0.75
        return 0.05

    def knowledge_queries(self, message: str) -> List[str]:
        return [
            message,
            "759 Blue Prince21 McKinzy brand story positioning tequila",
            "marketing playbook influencer outreach email templates",
            "759 Token ecosystem brand messaging",
        ]

    def role_instructions(self) -> str:
        return (
            "You are L.U.C.E.R.O Marketing Agent for Blue Prince21 McKinzy / 759. "
            "Produce polished, brand-safe marketing assets ready for review. "
            "Label drafts clearly. Prefer concrete calendars, captions, and CTAs."
        )
