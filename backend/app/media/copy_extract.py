"""Extract structured marketing copy fields from ACTION assistant replies."""

from __future__ import annotations

import re
from typing import Dict


def _field(text: str, labels: tuple[str, ...]) -> str:
    for label in labels:
        pat = rf"\*\*{re.escape(label)}:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)"
        m = re.search(pat, text or "", re.IGNORECASE | re.DOTALL)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def extract_flyer_copy(text: str) -> Dict[str, str]:
    headline = _field(text, ("Headline", "Title"))
    subhead = _field(text, ("Subheadline", "Subhead", "Subtitle"))
    body = _field(text, ("Body copy", "Body", "Main Text"))
    cta = _field(text, ("CTA", "Call to Action", "Call-to-Action"))
    if not headline:
        m = re.search(r"^#\s+(.+)$", text or "", re.MULTILINE)
        if m:
            headline = m.group(1).strip()
    return {
        "headline": headline or "Blue Prince21 McKinzy",
        "subhead": subhead or "Premium Additive-Free Tequila",
        "body": body
        or "100% additive-free. Blockchain-verified provenance. Drink it. Trade it. Own it.",
        "cta": cta or "Visit anthonywarrenmckinzy.com",
        "brand": "Blue Prince21 McKinzy",
        "tagline": "Drink it. Trade it. Own it.",
    }


def extract_slide_bullets(text: str, limit: int = 8) -> list[str]:
    bullets = re.findall(r"^\s*[-*•]\s+(.+)$", text or "", re.MULTILINE)
    if bullets:
        return [re.sub(r"\s+", " ", b).strip() for b in bullets[:limit]]
    # Fall back to short paragraphs
    parts = [p.strip() for p in re.split(r"\n\n+", text or "") if len(p.strip()) > 40]
    return [re.sub(r"\s+", " ", p)[:180] for p in parts[:limit]]
