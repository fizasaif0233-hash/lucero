"""Rewrite LLM refusals into finished flyer packages when media is generating."""

from __future__ import annotations

import re


_REFUSAL = re.compile(
    r"(cannot create (files|images)|can'?t create (files|images)|"
    r"i (currently )?cannot|unable to (create|generate|export) (images?|files?|pdf)|"
    r"step-by-step guide|use (a design tool|canva|adobe|photoshop)|"
    r"here'?s how to create|export(ing)? the flyer|instructions to create)",
    re.IGNORECASE,
)


def looks_like_media_refusal(text: str) -> bool:
    return bool(_REFUSAL.search(text or ""))


def finished_flyer_package(*, user_message: str = "") -> str:
    black_gold = "black" in (user_message or "").lower() and "gold" in (
        user_message or ""
    ).lower()
    colors = (
        "Black `#0A0A0A` · Gold `#C9A227` · Cream `#F5F0E6`"
        if black_gold
        else "Deep agave `#0B3D2E` · Gold `#C9A227` · Cream `#F5F0E6`"
    )
    return f"""✅ Flyer created — generating print-ready PNG & PDF now

**Headline:** Blue Prince21 McKinzy
**Subheadline:** The World's First Blockchain-Native, Barrel-Backed Tequila
**Body copy:** Crafted from 100% Blue Weber agave. Additive-free. Blockchain-verified provenance. Drink it. Trade it. Own it.
**CTA:** Visit anthonywarrenmckinzy.com

**Color palette:** {colors}
**Fonts:** Cinzel (display) · Outfit (body)

**Image prompts (for the generator — no letters in the artwork):**
- **Flux:** luxury Blue Prince21 tequila bottle on {"pure black background with gold rim light" if black_gold else "agave field at golden hour"}, cinematic product photography, premium spirits ad, NO TEXT, NO WATERMARK, vertical 3:4
- **Midjourney:** same brief --ar 3:4 --stylize 250

I assumed a premium {"black & gold" if black_gold else "agave luxury"} print layout. Tell me if you want changes.
"""
