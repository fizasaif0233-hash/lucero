"""Named media pipelines executed by JobService."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agents.os_task_router import (
    extract_image_prompt_from_reply,
    extract_narration_from_reply,
    extract_video_prompt_from_reply,
)
from app.core.config import Settings, get_settings
from app.media.image_gen import ImageGenerator
from app.media.video_gen import VideoGenerator
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_FLYER_PROMPT = (
    "Premium luxury tequila flyer, Blue Prince21 McKinzy bottle hero, "
    "agave fields at golden hour, deep agave green #0B3D2E and gold #C9A227, "
    "cream parchment, elegant typography space for headline, cinematic lighting, "
    "print-ready vertical poster composition, no blurry text"
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

    async def progress(pct: int, detail: str) -> None:
        if on_progress:
            await on_progress(pct, detail)

    if task_type in {"flyer_image", "instagram_ad", "logo", "image"}:
        await progress(10, "Building image prompt…")
        prompt = (
            input_data.get("prompt")
            or extract_image_prompt_from_reply(input_data.get("assistant_text") or "")
            or input_data.get("user_message")
            or DEFAULT_FLYER_PROMPT
        )
        if task_type == "logo":
            prompt = (
                f"Minimal luxury logo design for Blue Prince21 McKinzy tequila, "
                f"vector-friendly, gold and deep green, clean negative space. {prompt}"
            )
        aspect = input_data.get("aspect") or (
            "1:1" if task_type == "instagram_ad" else "3:4"
        )
        await progress(40, "Generating with FLUX (SDXL fallback)…")
        asset = await images.generate(
            user_id=user_id,
            prompt=str(prompt)[:1200],
            aspect=aspect,
            title=input_data.get("title") or task_type.replace("_", " ").title(),
        )
        await progress(100, "Image ready")
        return {"assets": [asset], "primary_url": asset.get("public_url")}

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
