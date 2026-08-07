"""Kokoro TTS via Replicate."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.config import Settings, get_settings
from app.media.replicate_client import ReplicateClient, ReplicateError
from app.media.storage import GeneratedStorage


def _audio_url(output: Any) -> Optional[str]:
    if isinstance(output, str) and output.startswith("http"):
        return output
    if isinstance(output, dict):
        return output.get("audio") or output.get("url") or output.get("wav")
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, str):
            return first
    return None


class TextToSpeech:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client = ReplicateClient(self._settings)
        self._storage = GeneratedStorage(self._settings)

    @property
    def enabled(self) -> bool:
        return self._client.enabled

    async def synthesize(
        self,
        *,
        user_id: str,
        text: str,
        voice: str = "af_bella",
        title: str = "Narration",
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise ReplicateError("REPLICATE_API_TOKEN not set")
        output = await self._client.run(
            self._settings.replicate_kokoro_model,
            {"text": text[:4500], "voice": voice, "speed": 1.0},
            timeout_s=180,
        )
        url = _audio_url(output)
        if not url:
            raise ReplicateError("Kokoro returned no audio URL")
        path, public, data = await self._storage.upload_from_url(
            user_id=user_id,
            url=url,
            ext="wav",
            mime="audio/wav",
            folder="audio",
        )
        return {
            "kind": "audio",
            "title": title,
            "storage_path": path,
            "public_url": public,
            "mime": "audio/wav",
            "byte_size": len(data),
            "meta": {"voice": voice, "model": self._settings.replicate_kokoro_model},
        }
