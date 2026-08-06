"""Customer Support Agent — FAQ, tastings, shipping, membership."""

from __future__ import annotations

import re
from typing import List

from app.agents.specialist_base import AgentInfo, SpecialistAgent


class SupportAgent(SpecialistAgent):
    info = AgentInfo(
        id="support",
        name="Customer Support",
        title="Customer Support",
        description="Answer product FAQs, tasting bookings, shipping, membership, and token questions.",
        skills=(
            "Product FAQ",
            "Book a tasting",
            "Shipping & payments",
            "Refunds & policies",
            "Membership & token questions",
            "Customer reply drafts",
        ),
        icon="headset",
        status="ready",
    )

    _PATTERNS = (
        r"\bcustomer\b",
        r"\bfaq\b",
        r"\btasting\b",
        r"\bship(ping)?\b",
        r"\brefund\b",
        r"\bpayment method",
        r"\bwhere are you located\b",
        r"\bdo you ship\b",
        r"\bbook a tasting\b",
        r"\bmembership\b",
        r"\bsupport\b",
        r"\bhow (do|can) i (buy|order|book)\b",
    )

    def relevance(self, message: str) -> float:
        lower = message.lower()
        hits = sum(1 for p in self._PATTERNS if re.search(p, lower))
        if re.search(r"\bwhat is 759 tequila\b", lower):
            return 0.85
        return min(0.9, 0.5 + 0.15 * hits) if hits else 0.08

    def knowledge_queries(self, message: str) -> List[str]:
        return [
            message,
            "759 Tequila FAQ tasting shipping payment location",
            "759 Private Exchange member onboarding tiers",
            "anthonywarrenmckinzy brand contact booking",
        ]

    def role_instructions(self) -> str:
        return (
            "You are L.U.C.E.R.O Customer Support. Be warm, clear, and accurate. "
            "Answer FAQs from knowledge. For bookings, outline steps and ask for missing details. "
            "Do not invent policies. Future channels: WhatsApp, Telegram, website widget."
        )
