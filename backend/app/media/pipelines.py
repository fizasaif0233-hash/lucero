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
from app.media.image_gen import ImageGenerator
from app.media.print_compose import PrintComposer
from app.media.pptx_gen import PresentationBuilder
from app.media.replicate_client import ReplicateError
from app.media.video_gen import VideoGenerator
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_FLYER_PROMPT = (
    "Premium luxury tequila flyer background only, NO TEXT, NO LETTERS, NO WATERMARK, "
    "Blue Prince21 McKinzy bottle hero, agave fields at golden hour, "
    "deep agave green and gold tones, cream accents, cinematic lighting, "
    "vertical 3:4 print composition, empty lower third for typography"
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

    # ---- Print-ready flyer / poster / social / logo ----
    if task_type in {
        "flyer_image",
        "instagram_ad",
        "logo",
        "image",
        "social_pack",
        "print_flyer",
    }:
        await progress(8, "Extracting finished copy…")
        assistant_text = input_data.get("assistant_text") or ""
        copy = extract_flyer_copy(assistant_text)
        prompt = (
            input_data.get("prompt")
            or extract_image_prompt_from_reply(assistant_text)
            or input_data.get("user_message")
            or DEFAULT_FLYER_PROMPT
        )
        # Force no-text backgrounds so print composer adds crisp type
        prompt = f"{str(prompt)[:1000]}. Absolutely no text, letters, or watermarks in the image."

        if task_type == "logo":
            prompt = (
                "Minimal luxury logo mark for Blue Prince21 McKinzy tequila, "
                "vector-friendly emblem, gold and deep green, centered, "
                "clean negative space, NO busy scene, NO paragraph text. "
                + prompt[:400]
            )

        aspect = input_data.get("aspect") or (
            "1:1"
            if task_type in {"instagram_ad", "social_pack", "logo"}
            else "3:4"
        )

        assets: List[Dict[str, Any]] = []
        bg_url: Optional[str] = None

        if images.enabled:
            await progress(35, "Generating FLUX/SDXL artwork…")
            try:
                art = await images.generate(
                    user_id=user_id,
                    prompt=prompt[:1200],
                    aspect=aspect,
                    title=input_data.get("title") or "Artwork",
                )
                assets.append(art)
                bg_url = art.get("public_url")
            except Exception as exc:
                logger.warning("artwork_failed_continuing_print", error=str(exc))
        else:
            await progress(
                35,
                "REPLICATE_API_TOKEN missing — composing print layout with brand canvas…",
            )

        # Logos: artwork is enough; still offer PNG download
        if task_type == "logo":
            if not assets:
                raise ReplicateError(
                    "Logo generation needs REPLICATE_API_TOKEN (FLUX/SDXL)."
                )
            await progress(100, "Logo ready")
            return {"assets": assets, "primary_url": assets[0].get("public_url")}

        await progress(70, "Composing print-ready PNG + PDF…")
        size = (1080, 1080) if task_type in {"instagram_ad", "social_pack"} else (2550, 3300)
        print_pack = await printer.compose_flyer(
            user_id=user_id,
            copy=copy,
            background_url=bg_url,
            title=input_data.get("title") or "Print-ready flyer",
            size=size,
        )
        assets.extend(print_pack.get("assets") or [])
        await progress(100, "Print files ready")
        return {
            "assets": assets,
            "primary_url": print_pack.get("primary_url")
            or (assets[-1].get("public_url") if assets else None),
            "png_url": print_pack.get("png_url"),
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
        await progress(5, "Preparing narration…")
        assistant_text = input_data.get("assistant_text") or ""
        narration = (
            input_data.get("narration")
            or extract_narration_from_reply(assistant_text)
            or input_data.get("user_message")
            or "Blue Prince21 McKinzy — Drink it. Trade it. Own it."
        )
        video_prompt = (
            input_data.get("video_prompt")
            or extract_video_prompt_from_reply(assistant_text)
            or (
                "Cinematic 30s tequila commercial, agave fields golden hour, "
                "premium bottle hero, luxury hospitality, slow camera push"
            )
        )
        scene_prompts: List[str] = input_data.get("scene_prompts") or []
        if not scene_prompts:
            img = extract_image_prompt_from_reply(assistant_text)
            if img:
                scene_prompts = [img]
        await progress(25, "Synthesizing Kokoro voiceover…")
        await progress(45, "Generating video (Wan → CogVideoX)…")
        result = await video.generate_commercial(
            user_id=user_id,
            narration=str(narration),
            video_prompt=str(video_prompt),
            scene_prompts=scene_prompts or None,
            voice=input_data.get("voice") or "af_bella",
            title=input_data.get("title") or "Commercial MP4",
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
