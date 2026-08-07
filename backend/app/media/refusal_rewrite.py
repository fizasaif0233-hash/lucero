"""Rewrite LLM refusals into finished flyer packages when media is generating."""

from __future__ import annotations

import re


_REFUSAL = re.compile(
    r"(cannot create (files|images)|can'?t create (files|images)|"
    r"i (currently )?cannot|unable to (create|generate|export) (images?|files?|pdf|downloadable)|"
    r"unable to generate downloadable|"
    r"step-by-step guide|use (a design tool|canva|adobe|photoshop)|"
    r"here'?s how to create|export(ing)? the flyer|instructions to create|"
    r"preferred platform|create the facebook ad on)",
    re.IGNORECASE,
)

# Model often invents fake Download PNG/PDF lines with no URL — strip them.
_FAKE_DOWNLOAD = re.compile(
    r"(?im)^(?:\s*(?:✅\s*)?(?:files? (?:are )?ready(?: for download)?!?|"
    r"generating print-ready files now\.{0,3}|"
    r"download(?:able)? (?:png|pdf|mp4|files?)|"
    r"⬇️?\s*download (?:png|pdf|mp4))\s*)+$"
    r"|(?im)^\s*(?:⬇️\s*)?download (?:png|pdf|mp4)\s*$"
    r"|(?im)^\s*✅\s*files? are ready for download!?\s*$"
)


def looks_like_media_refusal(text: str) -> bool:
    return bool(_REFUSAL.search(text or ""))


def strip_fake_download_claims(text: str) -> str:
    """Remove hallucinated download CTAs that have no real file URL."""
    if not text:
        return text
    # Drop markdown links that are not http(s)
    cleaned = re.sub(
        r"\[([^\]]*Download[^\]]*)\]\((?!https?://)[^)]*\)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if re.match(
            r"^(?:✅\s*)?(?:files? (?:are )?ready(?: for download)?!?|"
            r"generating print-ready files now\.{0,3}|"
            r"(?:⬇️\s*)?download (?:png|pdf|mp4))\s*$",
            stripped,
            re.IGNORECASE,
        ):
            continue
        if re.match(r"^download (png|pdf|mp4)\s*$", stripped, re.IGNORECASE):
            continue
        lines.append(line)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


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
