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


def _features_block(text: str) -> str:
    m = re.search(
        r"\*\*(?:Features|Feature list|Key features|Benefits):\*\*\s*(.+?)(?:\n\*\*|\n\n\*\*|$)",
        text or "",
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return m.group(1).strip()
    bullets = re.findall(r"^\s*[-*•]\s+(.+)$", text or "", re.MULTILINE)
    if len(bullets) >= 2:
        return "\n".join(f"- {b.strip()}" for b in bullets[:5])
    return ""


def extract_flyer_copy(text: str) -> Dict[str, str]:
    headline = _field(text, ("Headline", "Title"))
    subhead = _field(text, ("Subheadline", "Subhead", "Subtitle"))
    body = _field(text, ("Body copy", "Body", "Main Text"))
    cta = _field(text, ("CTA", "Call to Action", "Call-to-Action"))
    website = _field(text, ("Website", "URL", "Site"))
    contact = _field(text, ("Contact", "Contact info", "Email", "Phone"))
    features = _features_block(text)
    if not headline:
        m = re.search(r"^#\s+(.+)$", text or "", re.MULTILINE)
        if m:
            headline = m.group(1).strip()
    site = website or PRIMARY_WEBSITE
    return {
        "headline": headline or "EXPERIENCE TRUE PREMIUM TEQUILA",
        "subhead": subhead or "DRINK IT. TRADE IT. OWN IT.",
        "body": body
        or (
            "Blue Prince 21 McKinzy is more than tequila. It's a movement. "
            "Crafted for those who appreciate quality, authenticity, and legacy."
        ),
        "features": features
        or (
            "- 100% ADDITIVE-FREE | Pure. Clean. Authentic.\n"
            "- BLOCKCHAIN VERIFIED | Transparency you can trust.\n"
            "- PREMIUM QUALITY | Handcrafted to perfection.\n"
            "- COMMUNITY OWNED | Built for the people, by the people.\n"
            "- CRAFTED IN JALISCO, MEXICO | The heart of authentic tequila."
        ),
        "cta": cta or "ORDER NOW",
        "website": site,
        "contact": contact or site.replace("https://www.", "").replace("https://", ""),
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
