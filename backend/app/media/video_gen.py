"""Commercial video pipeline: VO + one video model → FFmpeg mux MP4.

Designed for Replicate accounts with burst=1 (serial predictions + cooldown).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.media.ffmpeg_mux import mux_commercial
from app.media.image_gen import _first_url
from app.media.replicate_client import ReplicateClient, ReplicateError
from app.media.storage import GeneratedStorage
from app.media.tts import TextToSpeech
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Free / low-credit Replicate accounts allow only 1 create burst — space calls out
_BURST_COOLDOWN_S = 12.0


class VideoGenerator:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client = ReplicateClient(self._settings)
        self._storage = GeneratedStorage(self._settings)
        self._tts = TextToSpeech(self._settings)

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
                "Configure it on Railway, or generate the storyboard/VO package from chat for now."
            )

        assets: List[Dict[str, Any]] = []

        # 1) Voiceover only (1 prediction) — skip scene stills to save burst quota
        vo = await self._tts.synthesize(
            user_id=user_id,
            text=narration,
            voice=voice,
            title="Commercial narration",
        )
        assets.append(vo)

        # Cool down so the next create is not immediately throttled (burst=1)
        await asyncio.sleep(_BURST_COOLDOWN_S)

        # 2) One primary video model, then at most one fallback after cooldown
        # Do NOT cascade 4 models × 2 attempts — that guarantees 429 on low-credit accounts
        last_err: Optional[Exception] = None
        base_video_url: Optional[str] = None
        used_model = ""
        prompt = (video_prompt or "").strip() or (
            "Cinematic luxury tequila bottle commercial, dark marble, gold rim light, "
            "slow camera push, photorealistic, no text overlays"
        )
        if scene_prompts:
            prompt = f"{prompt}. Scene focus: {scene_prompts[0][:200]}"

        model_attempts = [
            m
            for m in (
                self._settings.replicate_wan_model,
                self._settings.replicate_cogvideox_model,
            )
            if m
        ]

        for i, model in enumerate(model_attempts):
            try:
                output = await self._client.run(
                    model, {"prompt": prompt[:1200]}, timeout_s=600
                )
                url = _first_url(output)
                if not url and isinstance(output, str):
                    url = output
                if not url:
                    raise ReplicateError(f"No video URL from {model}")
                base_video_url = url
                used_model = model
                break
            except ReplicateError as exc:
                last_err = exc
                logger.warning("video_model_failed", model=model, error=str(exc))
                if getattr(exc, "status_code", None) == 429 or "429" in str(exc):
                    # Wait out the window, then try next model once
                    await asyncio.sleep(_BURST_COOLDOWN_S + 3.0)
                    continue
                if i + 1 < len(model_attempts):
                    await asyncio.sleep(_BURST_COOLDOWN_S)
            except Exception as exc:
                last_err = exc
                logger.warning("video_model_failed", model=model, error=str(exc))
                if i + 1 < len(model_attempts):
                    await asyncio.sleep(_BURST_COOLDOWN_S)

        if not base_video_url:
            detail = str(last_err) or "No video provider succeeded."
            if "429" in detail or "throttled" in detail.lower():
                raise ReplicateError(
                    "Replicate rate limit hit while generating the commercial. "
                    "Low-credit accounts only allow 1 prediction at a time. "
                    "Wait 20 seconds and ask again. "
                    "Also confirm Railway REPLICATE_API_TOKEN is from the same "
                    "Replicate account that has your $10 credit "
                    "(error shows <$5 credit if the token is a different account). "
                    f"Detail: {detail[:300]}",
                    status_code=429,
                )
            raise ReplicateError(detail)

        # 3) FFmpeg: merge VO + burn captions (+ optional music)
        final_bytes = await mux_commercial(
            video_url=base_video_url,
            audio_url=vo.get("public_url"),
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
                "engine": "replicate+ffmpeg",
                "video_model": used_model,
                "has_vo": True,
            },
        }
        assets.append(primary)
        return {"assets": assets, "primary": primary}
