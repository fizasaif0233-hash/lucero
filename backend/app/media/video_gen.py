"""Commercial video via bytedance/seedance-1-lite only.

Seedance clips are max 10s each — longer requests (e.g. 60s) are built by
generating multiple 10s segments and concatenating with FFmpeg.
"""

from __future__ import annotations

import asyncio
import math
import re
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.media.ffmpeg_mux import concat_videos, mux_commercial
from app.media.image_gen import _first_url
from app.media.replicate_client import ReplicateClient, ReplicateError
from app.media.storage import GeneratedStorage
from app.utils.logging import get_logger

logger = get_logger(__name__)

SEEDANCE_MODEL = "bytedance/seedance-1-lite"
_CLIP_MAX_S = 10  # Seedance-1-lite hard max per prediction
_BURST_COOLDOWN_S = 15.0


def parse_duration_seconds(
    *texts: str,
    default: int = 10,
    maximum: int = 60,
) -> int:
    """Pull requested length from user/assistant text (e.g. 60s, 30 second, 1 min)."""
    blob = " ".join(t or "" for t in texts).lower()
    # Prefer explicit seconds
    m = re.search(r"(\d+)\s*(?:s(?:ec(?:ond)?s?)?)\b", blob)
    if m:
        return max(5, min(maximum, int(m.group(1))))
    m = re.search(r"(\d+)\s*min(?:ute)?s?\b", blob)
    if m:
        return max(5, min(maximum, int(m.group(1)) * 60))
    # "60 second commercial" without unit glued
    m = re.search(r"\b(\d+)\s*second\b", blob)
    if m:
        return max(5, min(maximum, int(m.group(1))))
    return max(5, min(maximum, default))


def _seedance_payload(prompt: str, clip_s: int) -> Dict[str, Any]:
    # API accepts 5 or 10
    duration = 10 if clip_s >= 8 else 5
    return {
        "prompt": prompt[:1200],
        "duration": duration,
        "resolution": "720p",
        "aspect_ratio": "16:9",
    }


def _segment_prompts(
    *,
    base: str,
    narration: str,
    scene_prompts: Optional[List[str]],
    n: int,
) -> List[str]:
    scenes = [s.strip() for s in (scene_prompts or []) if s and s.strip()]
    if not scenes and narration:
        # Split VO into rough beats
        parts = re.split(r"(?<=[.!?])\s+", narration.strip())
        scenes = [p for p in parts if len(p) > 20][:n]
    while len(scenes) < n:
        scenes.append(
            f"continuation of the same luxury tequila commercial, beat {len(scenes) + 1}"
        )
    out: List[str] = []
    for i in range(n):
        beat = scenes[i % len(scenes)]
        out.append(
            f"{base}. Scene {i + 1} of {n}: {beat}. "
            "Same Blue Prince21 McKinzy sapphire bottle continuity, "
            "cinematic spirits ad, photorealistic, no on-screen text."
        )
    return out


class VideoGenerator:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client = ReplicateClient(self._settings)
        self._storage = GeneratedStorage(self._settings)
        self._model = (
            (self._settings.replicate_seedance_model or "").strip() or SEEDANCE_MODEL
        )

    @property
    def enabled(self) -> bool:
        return self._client.enabled

    async def _run_seedance(self, prompt: str, clip_s: int) -> str:
        payload = _seedance_payload(prompt, clip_s)
        output = await self._client.run(self._model, payload, timeout_s=600)
        url = _first_url(output)
        if not url and isinstance(output, str):
            url = output
        if not url and isinstance(output, dict):
            url = output.get("video") or output.get("url") or output.get("mp4")
        if not url:
            raise ReplicateError(f"No video URL from {self._model}")
        return url

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
        duration_seconds: Optional[int] = None,
        user_message: str = "",
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise ReplicateError(
                "Video generation needs REPLICATE_API_TOKEN. Configure it on Railway."
            )

        target_s = duration_seconds or parse_duration_seconds(
            user_message, video_prompt, narration, default=10, maximum=60
        )
        # Seedance max 10s/clip → number of segments
        clip_s = _CLIP_MAX_S if target_s > 5 else 5
        n_clips = max(1, min(6, math.ceil(target_s / clip_s)))  # cap 6 → 60s

        base = (video_prompt or "").strip() or (
            "Cinematic luxury tequila bottle commercial, dark marble, gold rim light, "
            "slow camera push, photorealistic spirits advertising, no on-screen text"
        )
        prompts = _segment_prompts(
            base=base,
            narration=narration or "",
            scene_prompts=scene_prompts,
            n=n_clips,
        )

        assets: List[Dict[str, Any]] = []
        clip_urls: List[str] = []
        last_err: Optional[Exception] = None

        for i, prompt in enumerate(prompts):
            try:
                if i > 0:
                    await asyncio.sleep(_BURST_COOLDOWN_S)
                url = await self._run_seedance(prompt, clip_s)
                clip_urls.append(url)
                logger.info(
                    "seedance_clip_ok",
                    clip=i + 1,
                    of=n_clips,
                    model=self._model,
                )
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "seedance_clip_failed",
                    clip=i + 1,
                    error=str(exc),
                )
                # If we already have at least one clip, stitch what we have
                if clip_urls:
                    break
                detail = str(exc)
                if "429" in detail or "throttled" in detail.lower() or "$5" in detail:
                    raise ReplicateError(
                        "Replicate rate limit on Seedance. Wait ~20s and retry. "
                        "Confirm Railway REPLICATE_API_TOKEN is from the account "
                        f"with credit. Detail: {detail[:280]}",
                        status_code=429,
                    ) from exc
                raise

        if not clip_urls:
            raise ReplicateError(str(last_err) or "Seedance returned no video")

        actual_s = len(clip_urls) * clip_s

        # Concatenate multi-clip commercials, then burn captions
        if len(clip_urls) == 1:
            video_bytes = await mux_commercial(
                video_url=clip_urls[0],
                audio_url=None,
                narration_text=narration,
                ffmpeg_bin=self._settings.ffmpeg_path,
                music_url=music_url,
                duration_hint=float(actual_s),
            )
        else:
            stitched = await concat_videos(
                clip_urls, ffmpeg_bin=self._settings.ffmpeg_path
            )
            # Upload temp stitch then mux captions from URL path — simpler: write via storage
            tmp_path, tmp_url = await self._storage.upload_bytes(
                user_id=user_id,
                data=stitched,
                ext="mp4",
                mime="video/mp4",
                folder="video",
            )
            video_bytes = await mux_commercial(
                video_url=tmp_url,
                audio_url=None,
                narration_text=narration,
                ffmpeg_bin=self._settings.ffmpeg_path,
                music_url=music_url,
                duration_hint=float(actual_s),
            )

        path, public = await self._storage.upload_bytes(
            user_id=user_id,
            data=video_bytes,
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
            "byte_size": len(video_bytes),
            "meta": {
                "engine": "seedance-1-lite",
                "video_model": self._model,
                "requested_seconds": target_s,
                "actual_seconds": actual_s,
                "clips": len(clip_urls),
                "clip_seconds": clip_s,
                "note": (
                    None
                    if actual_s >= target_s
                    else f"Seedance max is 10s/clip; built {len(clip_urls)}×{clip_s}s ≈ {actual_s}s"
                ),
            },
        }
        assets.append(primary)
        return {"assets": assets, "primary": primary}
