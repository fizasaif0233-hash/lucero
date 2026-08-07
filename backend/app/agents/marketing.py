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
            "Facebook / Instagram / LinkedIn / X ads & posts",
            "Email campaigns & newsletters",
            "Landing pages, sales pages & funnels",
            "SEO articles & product descriptions",
            "Press releases",
            "Commercial & YouTube / Rumble scripts",
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
        r"\bflyer\b",
        r"\bposter\b",
        r"\blanding page\b",
        r"\bsales (letter|page|copy)\b",
        r"\bslogan\b",
        r"\blogo\b",
        r"\byoutube\b|\brumble\b",
        r"\bpitch deck\b",
        r"\bwhitepaper\b",
    )

    def relevance(self, message: str) -> float:
        lower = message.lower()
        hits = sum(1 for p in self._PATTERNS if re.search(p, lower))
        if hits >= 2:
            return 0.95
        if hits == 1:
            return 0.85
        if re.search(
            r"\b(create|write|generate|draft|make|design)\b.+\b(post|email|script|flyer|poster|ad|commercial|plan)\b",
            lower,
        ):
            return 0.9
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
            "You are L.U.C.E.R.O Marketing Agent — ACTION mode.\n"
            "When the user asks to create marketing assets, IMMEDIATELY deliver the finished "
            "piece. Do not ask for colors, audience, size, logo, or style first.\n"
            "Assume premium luxury tequila / 759 brand defaults unless contradicted by docs.\n"
            "For flyers/posters/ads include: final copy, AI image prompt, colors, typography, "
            "layout, CTA, then one assumption line.\n"
            "For commercials include: timed script, narration, scenes, camera, captions, music, "
            "AI video prompt.\n"
            "Never return outlines unless asked. Max 0–2 questions only if truly blocked.\n"
            "Blend uploaded brand docs when relevant; otherwise use craft + general knowledge."
        )
