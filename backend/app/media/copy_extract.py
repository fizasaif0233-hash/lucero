"""Extract structured marketing copy fields from ACTION assistant replies."""

from __future__ import annotations

import re
from typing import Dict

from app.core.brand import PRIMARY_WEBSITE


def _field(text: str, labels: tuple[str, ...]) -> str:
    for label in labels:
        pat = rf"\*\*{re.escape(label)}:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)"
        m = re.search(pat, text or "", re.IGNORECASE | re.DOTALL)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def _clip_words(text: str, limit: int, fallback: str) -> str:
    words = (text or fallback).strip().split()
    if not words:
        words = fallback.split()
    return " ".join(words[:limit])


def extract_flyer_copy(text: str) -> Dict[str, str]:
    """Short overlay copy only — flyers keep the bottle photo as the hero."""
    headline = _field(text, ("Headline", "Title"))
    subhead = _field(text, ("Subheadline", "Subhead", "Subtitle"))
    cta = _field(text, ("CTA", "Call to Action", "Call-to-Action"))
    website = _field(text, ("Website", "URL", "Site"))
    contact = _field(text, ("Contact", "Contact info", "Email", "Phone"))
    if not headline:
        m = re.search(r"^#\s+(.+)$", text or "", re.MULTILINE)
        if m:
            headline = m.group(1).strip()
    site = website or PRIMARY_WEBSITE
    short_headline = _clip_words(headline, 5, "SIPPING ELEGANCE")
    short_sub = _clip_words(subhead, 6, "Drink it. Trade it. Own it.")
    short_cta = _clip_words(cta, 3, "TASTE IT")
    return {
        "headline": short_headline,
        "subhead": short_sub,
        "body": "",
        "features": "",
        "cta": short_cta.upper(),
        "website": site,
        "contact": contact or site.replace("https://www.", "").replace("https://", ""),
        "brand": "Blue Prince 21",
        "tagline": "Sipping Elegance",
    }


def extract_slide_bullets(text: str, limit: int = 8) -> list[str]:
    bullets = re.findall(r"^\s*[-*•]\s+(.+)$", text or "", re.MULTILINE)
    if bullets:
        return [re.sub(r"\s+", " ", b).strip() for b in bullets[:limit]]
    # Fall back to short paragraphs
    parts = [p.strip() for p in re.split(r"\n\n+", text or "") if len(p.strip()) > 40]
    return [re.sub(r"\s+", " ", p)[:180] for p in parts[:limit]]
