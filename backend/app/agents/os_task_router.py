"""OS task intent classification for media + web jobs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class OsPlan:
    intent: str
    media_job: Optional[str] = None
    wants_web: bool = False
    image_prompt_hint: str = ""
    notes: str = ""
    # Print/PPTX jobs do not require Replicate
    requires_replicate: bool = True


class OsTaskRouter:
    """Rule-based ACTION router — enqueue media without interviewing."""

    _IMAGE_INTENTS = (
        (r"\bflyer\b", "flyer_image", "flyer", False),
        (r"\bposter\b", "flyer_image", "poster", False),
        (r"\bbrochure\b", "flyer_image", "brochure", False),
        (r"\bbanner\b", "flyer_image", "banner", False),
        (r"\bbusiness card\b", "flyer_image", "business_card", False),
        (r"\bthumbnail\b", "flyer_image", "thumbnail", True),
        (r"\bproduct mockup\b|\bmockup\b", "flyer_image", "mockup", True),
        (r"\blogo\b", "logo", "logo", True),
        (
            r"\binstagram\b.*\b(ad|post)\b|\b(ad|post)\b.*\binstagram\b|\binstagram ad\b",
            "social_pack",
            "instagram_ad",
            False,
        ),
        (
            r"\bsocial (media )?(ad|post)s?\b|\bfacebook (ad|post)\b|\bad creative\b",
            "social_pack",
            "social_ad",
            False,
        ),
    )

    _VIDEO_INTENTS = (
        r"\bcommercial\b",
        r"\b30\s*second\b.*\b(video|commercial|ad)\b",
        r"\b(ai )?video\b",
        r"\byoutube (script|video|commercial)\b",
        r"\brumble\b",
    )

    _DECK_INTENTS = (
        r"\bpresentation\b",
        r"\bpitch deck\b",
        r"\bpowerpoint\b|\bpptx\b|\bslides?\b",
    )

    _WEB_INTENTS = (
        r"\bis\s+.+\s+real\b",
        r"\bare\s+.+\s+real\b",
        r"\blegit\b|\blegitimate\b|\bscam\b",
        r"\bfact[- ]?check\b|\bverify\b",
        r"\blatest\b|\bnews\b|\bresearch\b|\blook up\b|\bsearch (the )?(web|internet|online)\b",
    )

    def plan(self, message: str) -> OsPlan:
        lower = (message or "").lower().strip()
        wants_web = any(re.search(p, lower) for p in self._WEB_INTENTS)

        for pat in self._VIDEO_INTENTS:
            if re.search(pat, lower):
                return OsPlan(
                    intent="commercial",
                    media_job="commercial_video",
                    wants_web=wants_web,
                    image_prompt_hint=message,
                    notes="Script + VO + MP4",
                    requires_replicate=True,
                )

        for pat in self._DECK_INTENTS:
            if re.search(pat, lower):
                return OsPlan(
                    intent="presentation",
                    media_job="presentation",
                    wants_web=wants_web,
                    notes="Downloadable PPTX",
                    requires_replicate=False,
                )

        for pat, job, intent, needs_rep in self._IMAGE_INTENTS:
            if re.search(pat, lower):
                return OsPlan(
                    intent=intent,
                    media_job=job,
                    wants_web=wants_web,
                    image_prompt_hint=message,
                    notes="Print-ready PNG/PDF (+ artwork when Replicate configured)",
                    requires_replicate=needs_rep,
                )

        if re.search(r"\bbusiness plan\b", lower):
            return OsPlan(intent="business_plan", wants_web=wants_web)

        if wants_web:
            return OsPlan(intent="web_fact", wants_web=True)

        return OsPlan(intent="general")


def extract_image_prompt_from_reply(text: str) -> str:
    """Pull a Flux/Midjourney-ready prompt from ACTION flyer package if present."""
    if not text:
        return ""
    patterns = [
        r"\*\*Flux:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)",
        r"\*\*FLUX:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)",
        r"\*\*DALL·E[^\n]*:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)",
        r"\*\*DALL.?E[^\n]*:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)",
        r"\*\*Midjourney:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)",
        r"AI image (?:generation )?prompt[:\s]+(.+?)(?:\n\n|$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            prompt = m.group(1).strip()
            prompt = re.sub(r"\s+", " ", prompt)
            if len(prompt) > 40:
                return prompt[:1200]
    return ""


def extract_narration_from_reply(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"\*\*ElevenLabs narration:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)",
        r"\*\*Full VO script[^\n]*:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)",
        r"Voiceover \(V\.O\.\):\s*[\"']?(.+?)(?:\n\[|\n\n|$)",
    ]
    chunks: List[str] = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE | re.DOTALL):
            chunk = re.sub(r"\s+", " ", m.group(1)).strip()
            if chunk:
                chunks.append(chunk)
    if chunks:
        return " ".join(chunks)[:4500]
    clean = re.sub(r"[#*_>`]", " ", text)
    return re.sub(r"\s+", " ", clean).strip()[:2000]


def extract_video_prompt_from_reply(text: str) -> str:
    if not text:
        return ""
    m = re.search(
        r"\*\*AI video prompt:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:1500]
    return ""
