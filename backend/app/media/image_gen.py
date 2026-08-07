"""Image generation — Gemini (primary) with Replicate FLUX/SDXL fallback."""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import Settings, get_settings
from app.media.replicate_client import ReplicateClient, ReplicateError
from app.media.storage import GeneratedStorage
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ImageGenError(Exception):
    """Raised when no image provider can fulfill the request."""


def _first_url(output: Any) -> Optional[str]:
    if isinstance(output, str) and output.startswith("http"):
        return output
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url") or first.get("image")
    if isinstance(output, dict):
        return output.get("url") or output.get("image")
    return None


class ImageGenerator:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client = ReplicateClient(self._settings)
        self._storage = GeneratedStorage(self._settings)

    @property
    def enabled(self) -> bool:
        return bool(self._settings.gemini_api_key) or self._client.enabled

    @property
    def gemini_enabled(self) -> bool:
        return bool(self._settings.gemini_api_key)

    async def generate(
        self,
        *,
        user_id: str,
        prompt: str,
        aspect: str = "3:4",
        title: str = "Generated image",
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise ImageGenError(
                "No image provider configured. Set GEMINI_API_KEY or REPLICATE_API_TOKEN."
            )

        # Prefer Gemini when keyed — Replicate is fallback only
        if self.gemini_enabled:
            try:
                return await self._generate_gemini(
                    user_id=user_id, prompt=prompt, aspect=aspect, title=title
                )
            except Exception as exc:
                logger.warning("gemini_image_failed", error=str(exc))
                if not self._client.enabled:
                    raise ImageGenError(f"Gemini image generation failed: {exc}") from exc

        if not self._client.enabled:
            raise ImageGenError("REPLICATE_API_TOKEN not set")

        return await self._generate_replicate(
            user_id=user_id, prompt=prompt, aspect=aspect, title=title
        )

    async def _generate_gemini(
        self,
        *,
        user_id: str,
        prompt: str,
        aspect: str,
        title: str,
    ) -> Dict[str, Any]:
        model = self._settings.gemini_image_model
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        # Soft aspect guidance in prompt (Gemini image models vary on config support)
        aspect_hint = {
            "1:1": "square 1:1 composition",
            "16:9": "widescreen 16:9 composition",
            "9:16": "vertical 9:16 composition",
            "3:4": "vertical 3:4 portrait composition",
            "4:3": "horizontal 4:3 composition",
        }.get(aspect, f"{aspect} composition")
        full_prompt = f"{prompt.strip()}. {aspect_hint}."

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            },
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._settings.gemini_api_key,
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                detail = resp.text[:500]
                raise ImageGenError(
                    f"Gemini HTTP {resp.status_code}: {detail}"
                )
            data = resp.json()

        raw, mime = self._extract_gemini_image(data)
        if not raw:
            raise ImageGenError("Gemini returned no image data")

        ext = "png" if "png" in mime else "jpg"
        path, public = await self._storage.upload_bytes(
            user_id=user_id,
            data=raw,
            ext=ext,
            mime=mime,
            folder="images",
        )
        return {
            "kind": "image",
            "title": title,
            "storage_path": path,
            "public_url": public,
            "mime": mime,
            "byte_size": len(raw),
            "meta": {
                "prompt": prompt,
                "model": model,
                "aspect": aspect,
                "engine": "gemini",
            },
        }

    @staticmethod
    def _extract_gemini_image(data: Dict[str, Any]) -> tuple[Optional[bytes], str]:
        candidates = data.get("candidates") or []
        for cand in candidates:
            parts = ((cand.get("content") or {}).get("parts")) or []
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if not inline:
                    continue
                b64 = inline.get("data")
                mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                if b64:
                    return base64.b64decode(b64), mime
        return None, "image/png"

    async def _generate_replicate(
        self,
        *,
        user_id: str,
        prompt: str,
        aspect: str,
        title: str,
    ) -> Dict[str, Any]:
        last_err: Optional[Exception] = None
        attempts = [
            (
                self._settings.replicate_flux_model,
                {
                    "prompt": prompt,
                    "num_outputs": 1,
                    "aspect_ratio": aspect,
                    "output_format": "png",
                    "go_fast": True,
                },
            ),
            (
                self._settings.replicate_flux_dev_model,
                {
                    "prompt": prompt,
                    "num_outputs": 1,
                    "aspect_ratio": aspect,
                    "output_format": "png",
                    "guidance": 3.5,
                },
            ),
            (
                self._settings.replicate_sdxl_model,
                {
                    "prompt": prompt,
                    "negative_prompt": "blurry, low quality, watermark, text artifacts, letters",
                    "width": 1024,
                    "height": 1280 if aspect in {"3:4", "9:16"} else 1024,
                    "num_outputs": 1,
                },
            ),
        ]
        for model, payload in attempts:
            try:
                output = await self._client.run(model, payload, timeout_s=180)
                url = _first_url(output)
                if not url:
                    raise ReplicateError(f"No image URL from {model}")
                path, public, data = await self._storage.upload_from_url(
                    user_id=user_id,
                    url=url,
                    ext="png",
                    mime="image/png",
                    folder="images",
                )
                return {
                    "kind": "image",
                    "title": title,
                    "storage_path": path,
                    "public_url": public,
                    "mime": "image/png",
                    "byte_size": len(data),
                    "meta": {
                        "prompt": prompt,
                        "model": model,
                        "aspect": aspect,
                        "engine": "replicate",
                    },
                }
            except ReplicateError as exc:
                last_err = exc
                if getattr(exc, "status_code", None) == 429 or "429" in str(exc):
                    raise
                logger.warning("image_gen_model_failed", model=model, error=str(exc))
            except Exception as exc:
                last_err = exc
                logger.warning("image_gen_model_failed", model=model, error=str(exc))
        raise ReplicateError(str(last_err) or "Image generation failed")

    async def upscale(self, *, user_id: str, image_url: str) -> Dict[str, Any]:
        output = await self._client.run(
            self._settings.replicate_upscale_model,
            {"image": image_url, "scale": 2},
            timeout_s=180,
        )
        url = _first_url(output) or (output if isinstance(output, str) else None)
        if not url:
            raise ReplicateError("Upscale returned no URL")
        path, public, data = await self._storage.upload_from_url(
            user_id=user_id, url=url, ext="png", mime="image/png", folder="images"
        )
        return {
            "kind": "image",
            "title": "Upscaled image",
            "storage_path": path,
            "public_url": public,
            "mime": "image/png",
            "byte_size": len(data),
            "meta": {"tool": "upscale", "source": image_url},
        }

    async def remove_background(
        self, *, user_id: str, image_url: str
    ) -> Dict[str, Any]:
        output = await self._client.run(
            self._settings.replicate_remove_bg_model,
            {"image": image_url},
            timeout_s=180,
        )
        url = _first_url(output) or (output if isinstance(output, str) else None)
        if not url:
            raise ReplicateError("Remove-bg returned no URL")
        path, public, data = await self._storage.upload_from_url(
            user_id=user_id, url=url, ext="png", mime="image/png", folder="images"
        )
        return {
            "kind": "image",
            "title": "Background removed",
            "storage_path": path,
            "public_url": public,
            "mime": "image/png",
            "byte_size": len(data),
            "meta": {"tool": "remove_bg", "source": image_url},
        }

    async def variations(
        self, *, user_id: str, prompt: str, n: int = 2
    ) -> List[Dict[str, Any]]:
        results = []
        for i in range(max(1, min(n, 3))):
            asset = await self.generate(
                user_id=user_id,
                prompt=f"{prompt}. Variation {i + 1}, slightly different composition.",
                title=f"Variation {i + 1}",
            )
            results.append(asset)
        return results
