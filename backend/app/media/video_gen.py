"""Commercial video pipeline: VO + scenes + Wan/LTX/Hunyuan/CogVideoX → FFmpeg mux MP4."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.media.ffmpeg_mux import mux_commercial
from app.media.image_gen import ImageGenerator, _first_url
from app.media.replicate_client import ReplicateClient, ReplicateError
from app.media.storage import GeneratedStorage
from app.media.tts import TextToSpeech
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VideoGenerator:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client = ReplicateClient(self._settings)
        self._storage = GeneratedStorage(self._settings)
        self._images = ImageGenerator(self._settings)
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

        # 1) Voiceover (Kokoro → Fish Speech)
        vo = await self._tts.synthesize(
            user_id=user_id,
            text=narration,
            voice=voice,
            title="Commercial narration",
        )
        assets.append(vo)

        # 2) Optional scene still for i2v
        start_image_url: Optional[str] = None
        if scene_prompts:
            try:
                still = await self._images.generate(
                    user_id=user_id,
                    prompt=scene_prompts[0] + ". Cinematic 16:9, no text.",
                    aspect="16:9",
                    title="Scene 1 still",
                )
                assets.append(still)
                start_image_url = still.get("public_url")
            except Exception as exc:
                logger.warning("scene_still_failed", error=str(exc))

        # 3) Text/image-to-video providers (Wan → LTX → Hunyuan → CogVideoX)
        last_err: Optional[Exception] = None
        base_video_url: Optional[str] = None
        used_model = ""
        model_attempts = [
            (self._settings.replicate_wan_model, {"prompt": video_prompt}),
            (self._settings.replicate_ltx_model, {"prompt": video_prompt}),
            (self._settings.replicate_hunyuan_model, {"prompt": video_prompt}),
            (self._settings.replicate_cogvideox_model, {"prompt": video_prompt}),
        ]
        for model, payload in model_attempts:
            if not model:
                continue
            try:
                full = dict(payload)
                if start_image_url:
                    full["image"] = start_image_url
                try:
                    output = await self._client.run(model, full, timeout_s=600)
                except ReplicateError:
                    output = await self._client.run(
                        model, {"prompt": video_prompt}, timeout_s=600
                    )
                url = _first_url(output)
                if not url and isinstance(output, str):
                    url = output
                if not url:
                    raise ReplicateError(f"No video URL from {model}")
                base_video_url = url
                used_model = model
                break
            except Exception as exc:
                last_err = exc
                logger.warning("video_model_failed", model=model, error=str(exc))

        if not base_video_url:
            raise ReplicateError(
                str(last_err)
                or "No video provider succeeded (Wan / LTX / Hunyuan / CogVideoX)."
            )

        # 4) FFmpeg: merge VO + burn captions (+ optional music)
        final_bytes = await mux_commercial(
            video_url=base_video_url,
            audio_url=vo.get("public_url"),
            narration_text=narration,
            ffmpeg_bin=self._settings.ffmpeg_path,
            music_url=music_url,
            duration_hint=30.0,
        )
        path, public = await self._storage.upload_bytes(
            user_id=user_id,
            data=final_bytes,
            ext="mp4",
            mime="video/mp4",
            folder="videos",
        )
        video_asset = {
            "kind": "video",
            "title": title,
            "storage_path": path,
            "public_url": public,
            "mime": "video/mp4",
            "byte_size": len(final_bytes),
            "meta": {
                "model": used_model,
                "video_prompt": video_prompt,
                "voice_url": vo.get("public_url"),
                "captions": "burned-in via FFmpeg",
                "mux": "ffmpeg",
            },
        }
        assets.append(video_asset)
        return {"primary": video_asset, "assets": assets}
