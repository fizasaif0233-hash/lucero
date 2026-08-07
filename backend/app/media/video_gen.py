"""Commercial video pipeline: VO + scene stills + Wan/CogVideoX → MP4."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
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
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise ReplicateError("REPLICATE_API_TOKEN not set")

        assets: List[Dict[str, Any]] = []

        # 1) Voiceover
        vo = await self._tts.synthesize(
            user_id=user_id,
            text=narration,
            voice=voice,
            title="Commercial narration",
        )
        assets.append(vo)

        # 2) Optional scene still (first scene) for image-to-video when supported
        start_image_url: Optional[str] = None
        if scene_prompts:
            try:
                still = await self._images.generate(
                    user_id=user_id,
                    prompt=scene_prompts[0],
                    aspect="16:9",
                    title="Scene 1 still",
                )
                assets.append(still)
                start_image_url = still.get("public_url")
            except Exception as exc:
                logger.warning("scene_still_failed", error=str(exc))

        # 3) Text/image-to-video
        last_err: Optional[Exception] = None
        for model, payload in (
            (
                self._settings.replicate_wan_model,
                {
                    "prompt": video_prompt,
                    **({"image": start_image_url} if start_image_url else {}),
                },
            ),
            (
                self._settings.replicate_cogvideox_model,
                {
                    "prompt": video_prompt,
                    **({"image": start_image_url} if start_image_url else {}),
                },
            ),
        ):
            try:
                # Models differ; strip unknown keys if needed by retrying minimal prompt
                try:
                    output = await self._client.run(model, payload, timeout_s=600)
                except ReplicateError:
                    output = await self._client.run(
                        model, {"prompt": video_prompt}, timeout_s=600
                    )
                url = _first_url(output)
                if not url and isinstance(output, str):
                    url = output
                if not url:
                    raise ReplicateError(f"No video URL from {model}")
                path, public, data = await self._storage.upload_from_url(
                    user_id=user_id,
                    url=url,
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
                    "byte_size": len(data),
                    "meta": {
                        "model": model,
                        "video_prompt": video_prompt,
                        "voice_url": vo.get("public_url"),
                        "captions_note": "Burned captions depend on model; SRT in chat package.",
                    },
                }
                assets.append(video_asset)
                return {"primary": video_asset, "assets": assets}
            except Exception as exc:
                last_err = exc
                logger.warning("video_model_failed", model=model, error=str(exc))

        raise ReplicateError(str(last_err) or "Video generation failed")
