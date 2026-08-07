"""Named media pipelines executed by JobService."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agents.os_task_router import (
    extract_image_prompt_from_reply,
    extract_narration_from_reply,
    extract_video_prompt_from_reply,
)
from app.core.config import Settings, get_settings
from app.media.copy_extract import extract_flyer_copy
from app.media.image_gen import ImageGenError, ImageGenerator
from app.media.print_compose import A4_300_DPI, PrintComposer
from app.media.pptx_gen import PresentationBuilder
from app.media.replicate_client import ReplicateError
from app.media.video_gen import VideoGenerator
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_FLYER_PROMPT = (
    "Cinematic luxury tequila advertisement photograph, Blue Prince21 McKinzy "
    "sapphire-blue glass bottle standing on the RIGHT side of frame on dark wet stone, "
    "agave field landscape at dramatic sunset filling the background left and center, "
    "golden hour rim light, deep navy and gold mood, vertical 3:4 composition, "
    "keep the LEFT third darker with empty space for typography overlay, "
    "photorealistic spirits advertising, NO TEXT, NO LETTERS, NO WATERMARK, NO LOGO TEXT"
)

DEFAULT_SOCIAL_PROMPT = (
    "Ultra-premium Facebook / Instagram advertisement photo for Blue Prince21 McKinzy tequila, "
    "hero shot of a luxury crystal tequila bottle center frame, dark cinematic lighting, "
    "agave leaves and gold rim light, rich emerald and gold color grade, "
    "photorealistic spirits advertising, shallow depth of field, empty lower third for headline, "
    "NO TEXT, NO LETTERS, NO WATERMARK, NO TYPOGRAPHY"
)

DEFAULT_LANDING_HERO = (
    "Cinematic website hero photograph for Blue Prince21 McKinzy tequila brand, "
    "luxury bottle on dark agave-green and gold backdrop, aerial agave fields soft in background, "
    "widescreen 16:9 composition, empty left third for headline typography, "
    "photorealistic premium spirits advertising, NO TEXT, NO LETTERS, NO WATERMARK"
)

DEFAULT_LANDING_ABOUT = (
    "Premium lifestyle photograph of Blue Weber agave fields at golden hour in Jalisco, "
    "cinematic wide shot, deep green and gold tones, NO TEXT, NO WATERMARK"
)


async def run_pipeline(
    task_type: str,
    *,
    user_id: str,
    input_data: Dict[str, Any],
    settings: Optional[Settings] = None,
    on_progress=None,
) -> Dict[str, Any]:
    cfg = settings or get_settings()
    images = ImageGenerator(cfg)
    video = VideoGenerator(cfg)
    printer = PrintComposer()

    async def progress(pct: int, detail: str) -> None:
        if on_progress:
            await on_progress(pct, detail)

    # ---- Landing page: Replicate hero + section images + composed mockup ----
    if task_type == "landing_page":
        if not images.enabled:
            raise ReplicateError(
                "REPLICATE_API_TOKEN is required to generate landing page images."
            )
        await progress(10, "Extracting landing copy…")
        assistant_text = input_data.get("assistant_text") or ""
        copy = extract_flyer_copy(assistant_text)
        user_message = str(input_data.get("user_message") or "")
        hero_prompt = (
            extract_image_prompt_from_reply(assistant_text)
            or DEFAULT_LANDING_HERO
        )
        hero_prompt = (
            f"{str(hero_prompt)[:900]}. Widescreen website hero, Blue Prince21 McKinzy "
            "tequila bottle, luxury brand photography, NO TEXT, NO LETTERS, NO WATERMARK."
        )
        assets: List[Dict[str, Any]] = []

        # One Replicate call only (free accounts: burst of 1 prediction)
        await progress(35, "Replicate FLUX — landing hero (1 image)…")
        hero = await images.generate(
            user_id=user_id,
            prompt=hero_prompt[:1200],
            aspect="16:9",
            title="Landing hero (Replicate FLUX)",
        )
        assets.append(hero)

        await progress(70, "Composing landing-page mockup PNG…")
        theme = (
            "black_gold"
            if ("black" in user_message.lower() and "gold" in user_message.lower())
            else "agave"
        )
        mock = await printer.compose_flyer(
            user_id=user_id,
            copy={
                **copy,
                "headline": copy.get("headline")
                or "The World's First Blockchain-Native, Barrel-Backed Tequila",
                "subhead": copy.get("subhead")
                or "Drink it. Trade it. Own it.",
                "cta": copy.get("cta") or "Join the Movement",
            },
            background_url=hero.get("public_url"),
            title="Landing page mockup",
            size=(1920, 1080),
            theme=theme,
            require_background=True,
        )
        assets.extend(mock.get("assets") or [])
        await progress(100, "Landing images ready")
        return {
            "assets": assets,
            "primary_url": hero.get("public_url"),
            "png_url": mock.get("png_url") or hero.get("public_url"),
            "engine": "replicate+landing",
        }

    # ---- Pure Replicate image (hero visual / photo) — no flyer layout ----
    if task_type == "image":
        if not images.enabled:
            raise ImageGenError(
                "REPLICATE_API_TOKEN is required to generate images."
            )
        await progress(10, "Building image prompt from your request…")
        assistant_text = input_data.get("assistant_text") or ""
        user_message = str(input_data.get("user_message") or "")
        prompt = (
            input_data.get("prompt")
            or extract_image_prompt_from_reply(assistant_text)
            or user_message
            or DEFAULT_FLYER_PROMPT
        )
        # Keep the creative brief intact — only a light quality nudge
        prompt = str(prompt).strip()[:1100]
        if "no text" not in prompt.lower() and "no letters" not in prompt.lower():
            prompt = (
                f"{prompt}. Photorealistic commercial photography, ultra detailed, "
                "NO extra UI chrome, NO watermark."
            )

        await progress(40, "Replicate FLUX generating your image…")
        art = await images.generate(
            user_id=user_id,
            prompt=prompt[:1200],
            aspect=input_data.get("aspect") or "3:4",
            title=input_data.get("title") or "Replicate FLUX — hero visual",
        )
        await progress(100, "Image ready")
        return {
            "assets": [art],
            "primary_url": art.get("public_url"),
            "png_url": art.get("public_url"),
            "engine": "replicate",
        }

    # ---- Print-ready flyer / poster / social / logo ----
    if task_type in {
        "flyer_image",
        "instagram_ad",
        "logo",
        "social_pack",
        "print_flyer",
    }:
        await progress(8, "Extracting finished copy…")
        assistant_text = input_data.get("assistant_text") or ""
        copy = extract_flyer_copy(assistant_text)
        user_message = str(input_data.get("user_message") or "")
        is_social = task_type in {"instagram_ad", "social_pack"}
        is_logo = task_type == "logo"

        # Social + logos MUST use Replicate — never return the green fallback canvas
        if (is_social or is_logo) and not images.enabled:
            raise ReplicateError(
                "REPLICATE_API_TOKEN is not set on Railway. "
                "Facebook/Instagram posts and logos require Replicate FLUX."
            )

        base_prompt = (
            DEFAULT_SOCIAL_PROMPT
            if is_social
            else DEFAULT_FLYER_PROMPT
        )
        prompt = (
            input_data.get("prompt")
            or extract_image_prompt_from_reply(assistant_text)
            or base_prompt
        )
        # Always reinforce no-text + brand bottle for Replicate
        prompt = (
            f"{str(prompt)[:900]}. "
            "Photorealistic Blue Prince21 McKinzy tequila bottle hero shot, "
            "luxury spirits advertising photography, cinematic lighting, "
            "Absolutely NO text, letters, logos-as-text, or watermarks in the image."
        )

        if is_logo:
            prompt = (
                "Minimal luxury logo emblem for Blue Prince21 McKinzy tequila brand, "
                "gold and deep green, vector-friendly mark on dark background, "
                "clean negative space, NO paragraph text, NO busy scene. "
                + prompt[:400]
            )

        aspect = input_data.get("aspect") or (
            "1:1" if is_social or is_logo else "3:4"
        )

        assets: List[Dict[str, Any]] = []
        bg_url: Optional[str] = None

        user_msg = user_message.lower()
        asst = assistant_text.lower()
        blob = f"{user_msg}\n{asst}"
        theme = (
            "black_gold"
            if (
                ("black" in blob and "gold" in blob)
                or "black and gold" in blob
                or "black & gold" in blob
                or "#0a0a0a" in blob
                or "#000000" in blob
            )
            else "agave"
        )

        if theme == "black_gold":
            prompt = (
                f"{prompt} Pure black background, gold rim light, "
                "black and gold luxury palette, premium night studio shot."
            )

        if images.enabled:
            await progress(30, "Generating Replicate FLUX artwork…")
            try:
                art = await images.generate(
                    user_id=user_id,
                    prompt=prompt[:1200],
                    aspect=aspect,
                    title=(
                        "Replicate FLUX — Facebook/Instagram post"
                        if is_social
                        else input_data.get("title") or "Replicate FLUX artwork"
                    ),
                )
                assets.append(art)
                bg_url = art.get("public_url")
            except Exception as exc:
                logger.warning("artwork_failed", error=str(exc))
                if is_social or is_logo:
                    raise ReplicateError(
                        f"Replicate image generation failed: {exc}. "
                        "Check REPLICATE_API_TOKEN and model access on Railway."
                    ) from exc
        else:
            await progress(
                30,
                "REPLICATE_API_TOKEN missing — print layout only (no AI photo)…",
            )

        if is_logo:
            await progress(100, "Logo ready")
            return {"assets": assets, "primary_url": assets[0].get("public_url")}

        # Social: Replicate photo is required; overlay crisp CTA type on top
        if is_social and not bg_url:
            raise ReplicateError(
                "Replicate did not return an image URL for this Facebook/Instagram post."
            )

        await progress(
            70,
            "Composing print-ready A4 flyer (logo, features, CTA, QR, PNG+PDF)…"
            if not is_social
            else "Composing finished social PNG with CTA…",
        )
        size = (1080, 1080) if is_social else A4_300_DPI

        # If black/gold requested but first art failed theme, try once more
        if theme == "black_gold" and images.enabled and not bg_url:
            art = await images.generate(
                user_id=user_id,
                prompt=(
                    "Luxury tequila bottle on pure black background, gold rim light, "
                    "cinematic product shot, NO TEXT, NO LETTERS, premium spirits advertising"
                ),
                aspect="3:4" if not is_social else "1:1",
                title="Replicate FLUX — black & gold",
            )
            assets.append(art)
            bg_url = art.get("public_url")

        print_pack = await printer.compose_flyer(
            user_id=user_id,
            copy=copy,
            background_url=bg_url,
            title=input_data.get("title")
            or ("Facebook post" if is_social else "Print-ready A4 flyer"),
            size=size,
            theme=theme,
            require_background=is_social,
            page_size="square" if is_social else "a4",
        )
        assets.extend(print_pack.get("assets") or [])
        await progress(100, "Files ready (Replicate + print overlay)")
        return {
            "assets": assets,
            "primary_url": print_pack.get("primary_url")
            or (assets[-1].get("public_url") if assets else None),
            "png_url": print_pack.get("png_url"),
            "engine": "replicate+compose" if bg_url else "compose-only",
        }

    # ---- PowerPoint ----
    if task_type in {"presentation", "pptx", "pitch_deck"}:
        await progress(20, "Building PowerPoint…")
        deck = await PresentationBuilder().build(
            user_id=user_id,
            assistant_text=str(input_data.get("assistant_text") or ""),
            title=input_data.get("title") or "L.U.C.E.R.O Presentation",
        )
        await progress(100, "PPTX ready")
        return deck

    if task_type in {"upscale", "remove_bg", "variations"}:
        await progress(20, f"Running {task_type}…")
        image_url = input_data.get("image_url") or ""
        if task_type == "upscale":
            asset = await images.upscale(user_id=user_id, image_url=image_url)
            return {"assets": [asset], "primary_url": asset.get("public_url")}
        if task_type == "remove_bg":
            asset = await images.remove_background(user_id=user_id, image_url=image_url)
            return {"assets": [asset], "primary_url": asset.get("public_url")}
        prompt = input_data.get("prompt") or DEFAULT_FLYER_PROMPT
        assets = await images.variations(user_id=user_id, prompt=str(prompt), n=2)
        return {
            "assets": assets,
            "primary_url": assets[0].get("public_url") if assets else None,
        }

    if task_type in {"commercial_video", "video"}:
        await progress(5, "Preparing Seedance commercial…")
        assistant_text = input_data.get("assistant_text") or ""
        user_message = str(input_data.get("user_message") or "")
        narration = (
            input_data.get("narration")
            or extract_narration_from_reply(assistant_text)
            or user_message
            or "Blue Prince21 McKinzy — Drink it. Trade it. Own it."
        )
        video_prompt = (
            input_data.get("video_prompt")
            or extract_video_prompt_from_reply(assistant_text)
            or (
                "Cinematic luxury tequila commercial, agave fields golden hour, "
                "premium Blue Prince21 McKinzy bottle hero, slow camera push"
            )
        )
        scene_prompts: List[str] = input_data.get("scene_prompts") or []
        if not scene_prompts:
            img = extract_image_prompt_from_reply(assistant_text)
            if img:
                scene_prompts = [img]
        # Pull timed scene lines from assistant package when present
        if not scene_prompts or len(scene_prompts) < 2:
            import re

            found = re.findall(
                r"Scene\s+\d+\s*\([^)]*\):\s*(.+?)(?:\n|$)",
                assistant_text,
                flags=re.I,
            )
            if found:
                scene_prompts = [re.sub(r"\s+", " ", f).strip()[:240] for f in found]

        from app.media.video_gen import parse_duration_seconds

        duration_s = parse_duration_seconds(
            user_message, assistant_text, str(video_prompt), default=10, maximum=60
        )
        n_est = max(1, min(6, (duration_s + 9) // 10))
        await progress(
            20,
            f"Seedance-1-lite: ~{duration_s}s via {n_est}×10s clip(s)…",
        )
        result = await video.generate_commercial(
            user_id=user_id,
            narration=str(narration),
            video_prompt=str(video_prompt),
            scene_prompts=scene_prompts or None,
            voice=input_data.get("voice") or "af_bella",
            title=input_data.get("title") or "Commercial MP4",
            duration_seconds=duration_s,
            user_message=user_message,
        )
        await progress(100, "Video ready")
        primary = result["primary"]
        return {
            "assets": result["assets"],
            "primary_url": primary.get("public_url"),
            "voice_url": next(
                (
                    a.get("public_url")
                    for a in result["assets"]
                    if a.get("kind") == "audio"
                ),
                None,
            ),
        }

    if task_type == "tts":
        from app.media.tts import TextToSpeech

        await progress(30, "Synthesizing speech…")
        tts = TextToSpeech(cfg)
        asset = await tts.synthesize(
            user_id=user_id,
            text=str(input_data.get("text") or ""),
            voice=input_data.get("voice") or "af_bella",
            title=input_data.get("title") or "TTS",
        )
        await progress(100, "Audio ready")
        return {"assets": [asset], "primary_url": asset.get("public_url")}

    raise ValueError(f"Unknown task_type: {task_type}")
