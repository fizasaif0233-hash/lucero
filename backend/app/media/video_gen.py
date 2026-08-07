"""Commercial video via ONE modern Replicate T2V model (burst=1 safe).

Uses current Replicate catalog models (Wan 2.5 / Seedance / Kling / Hailuo).
Skips separate TTS predictions so a commercial is a single API create.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.media.ffmpeg_mux import mux_commercial
from app.media.image_gen import _first_url
from app.media.replicate_client import ReplicateClient, ReplicateError
from app.media.storage import GeneratedStorage
from app.utils.logging import get_logger

logger = get_logger(__name__)

_BURST_COOLDOWN_S = 15.0


def _video_models(settings: Settings) -> List[str]:
    raw = (settings.replicate_video_models or "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    # Sensible defaults from Replicate's current recommended catalog
    return [
        settings.replicate_wan_model,
        settings.replicate_seedance_model,
        settings.replicate_kling_model,
        settings.replicate_hailuo_model,
    ]


def _payload_for_model(model: str, prompt: str) -> Dict[str, Any]:
    """Best-effort input schema per popular Replicate video model family."""
    m = model.lower()
    p = prompt[:1200]
    if "kling" in m:
        return {
            "prompt": p,
            "duration": 5,
            "aspect_ratio": "16:9",
        }
    if "seedance" in m:
        return {
            "prompt": p,
            "duration": 5,
            "resolution": "720p",
            "aspect_ratio": "16:9",
        }
    if "hailuo" in m or "video-01" in m or "minimax" in m:
        return {
            "prompt": p,
            "duration": 6,
        }
    if "veo" in m:
        return {
            "prompt": p,
            "aspect_ratio": "16:9",
        }
    if "grok" in m:
        return {
            "prompt": p,
            "aspect_ratio": "16:9",
        }
    if "pixverse" in m:
        return {
            "prompt": p,
            "duration": 5,
            "aspect_ratio": "16:9",
        }
    # Wan / LTX / generic
    return {"prompt": p}


class VideoGenerator:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client = ReplicateClient(self._settings)
        self._storage = GeneratedStorage(self._settings)

    @property
    def enabled(self) -> bool:
        return self._client.enabled

    async def generate_commercial(
        self,
        *,
        user_id: str,
        narration: str,
        video_prompt: str,
        scene_prompts: Optional[List[str]] = None,
        voice: str = "af_bella",
        title: str = "Commercial MP4",
        music_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise ReplicateError(
                "Video generation needs REPLICATE_API_TOKEN. "
                "Configure it on Railway."
            )

        assets: List[Dict[str, Any]] = []
        prompt = (video_prompt or "").strip() or (
            "Cinematic luxury tequila bottle commercial, dark marble, gold rim light, "
            "slow camera push, photorealistic spirits advertising, no on-screen text"
        )
        if narration:
            prompt = (
                f"{prompt}. Mood matches this VO: {narration[:280]}"
            )
        if scene_prompts:
            prompt = f"{prompt}. Key visual: {scene_prompts[0][:200]}"

        # ONE prediction only — no TTS/still cascade (burst=1 accounts)
        last_err: Optional[Exception] = None
        base_video_url: Optional[str] = None
        used_model = ""
        models = [m for m in _video_models(self._settings) if m]

        for i, model in enumerate(models):
            try:
                payload = _payload_for_model(model, prompt)
                output = await self._client.run(model, payload, timeout_s=600)
                url = _first_url(output)
                if not url and isinstance(output, str):
                    url = output
                if not url and isinstance(output, dict):
                    url = (
                        output.get("video")
                        or output.get("url")
                        or output.get("mp4")
                    )
                if not url:
                    raise ReplicateError(f"No video URL from {model}")
                base_video_url = url
                used_model = model
                break
            except ReplicateError as exc:
                last_err = exc
                logger.warning("video_model_failed", model=model, error=str(exc))
                if getattr(exc, "status_code", None) == 429 or "429" in str(exc):
                    if i + 1 < len(models):
                        await asyncio.sleep(_BURST_COOLDOWN_S)
                    continue
                # Schema mismatch — try next model after short pause
                if i + 1 < len(models):
                    await asyncio.sleep(2.0)
            except Exception as exc:
                last_err = exc
                logger.warning("video_model_failed", model=model, error=str(exc))
                if i + 1 < len(models):
                    await asyncio.sleep(2.0)

        if not base_video_url:
            detail = str(last_err) or "No video provider succeeded."
            if "429" in detail or "throttled" in detail.lower() or "<$5" in detail or "$5" in detail:
                raise ReplicateError(
                    "Replicate still rate-limits this API token (burst=1 / low credit). "
                    "Railway REPLICATE_API_TOKEN must be from the SAME account that has "
                    "your $10 balance — the API still reports <$5 credit for this token. "
                    "On replicate.com: Account → API tokens → copy a fresh token → "
                    "set REPLICATE_API_TOKEN on Railway lucero-api → redeploy. "
                    "Then wait 20s and ask for the commercial again. "
                    f"Detail: {detail[:280]}",
                    status_code=429,
                )
            raise ReplicateError(detail)

        # Burn captions from narration; keep model-native audio if present (no extra TTS call)
        final_bytes = await mux_commercial(
            video_url=base_video_url,
            audio_url=None,
            narration_text=narration,
            ffmpeg_bin=self._settings.ffmpeg_path,
            music_url=music_url,
        )
        path, public = await self._storage.upload_bytes(
            user_id=user_id,
            data=final_bytes,
            ext="mp4",
            mime="video/mp4",
            folder="video",
        )
        primary = {
            "kind": "video",
            "title": title,
            "storage_path": path,
            "public_url": public,
            "mime": "video/mp4",
            "byte_size": len(final_bytes),
            "meta": {
                "engine": "replicate",
                "video_model": used_model,
                "has_vo": False,
                "single_prediction": True,
            },
        }
        assets.append(primary)
        return {"assets": assets, "primary": primary}
