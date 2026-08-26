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
            "Flyers, posters & ads (Canva-ready packages)",
            "Commercial & YouTube / Rumble production packages",
            "30-day campaigns",
            "Facebook / Instagram / LinkedIn / X ads & posts",
            "Email campaigns & newsletters",
            "Landing pages, sales pages & funnels",
            "SEO articles & product descriptions",
            "Press releases",
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
        r"\bcanva\b",
        r"\bmidjourney\b|\bdall.?e\b|\bflux\b|\bleonardo\b",
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
            "You are L.U.C.E.R.O Marketing Agent — ACTION-first for Blue Prince21 McKinzy / 759.\n"
            "Open with ✅ status (e.g. ✅ Flyer created). Never open with Here's/Feel free/You can adjust.\n"
            "Assume sticky brand defaults (slogan Drink it. Trade it. Own it., palette, fonts) — never ask which company.\n"
            "FLYER/POSTER/AD package MUST include: Headline, Subheadline, Body, CTA, "
            "hex colors, fonts, and Flux/Midjourney image prompts (no text in artwork). "
            "Do not describe a flyer in prose; deliver the package.\n"
            "NEVER give Canva/Illustrator/Photoshop tutorials. NEVER say export from Canva.\n"
            "For flyers/ads, the print engine uses the official real Blue Prince 21 bottles "
            "(Blanco, Añejo, or both) — never invent a substitute bottle.\n"
            "COMMERCIAL package MUST include: timed VO, narration + voice direction, "
            "scene-by-scene (camera + captions), music, master AI video prompt, optional per-scene prompts.\n"
            "Max 1 clarifying question only if truly blocked. One short assumption line at the end optional."
        )
