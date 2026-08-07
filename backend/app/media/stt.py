"""Whisper Large V3 STT via Replicate."""

from __future__ import annotations

from typing import Any, Optional

from app.core.config import Settings, get_settings
from app.media.replicate_client import ReplicateClient, ReplicateError


class SpeechToText:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client = ReplicateClient(self._settings)

    @property
    def enabled(self) -> bool:
        return self._client.enabled

    async def transcribe(
        self,
        *,
        audio_url: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
        language: Optional[str] = None,
    ) -> str:
        if not self.enabled:
            raise ReplicateError("REPLICATE_API_TOKEN not set")
        if not audio_url and not audio_bytes:
            raise ReplicateError("audio_url or audio_bytes required")

        # Prefer URL input; for bytes, data URI
        audio_input: Any
        if audio_url:
            audio_input = audio_url
        else:
            import base64

            b64 = base64.b64encode(audio_bytes or b"").decode("ascii")
            audio_input = f"data:audio/webm;base64,{b64}"

        payload: dict = {
            "audio": audio_input,
            "model": "large-v3",
            "translate": False,
        }
        if language:
            payload["language"] = language

        output = await self._client.run(
            self._settings.replicate_whisper_model,
            payload,
            timeout_s=180,
        )
        if isinstance(output, str):
            return output.strip()
        if isinstance(output, dict):
            text = output.get("transcription") or output.get("text") or ""
            return str(text).strip()
        if isinstance(output, list) and output:
            return str(output[0]).strip()
        raise ReplicateError("Whisper returned empty transcript")
