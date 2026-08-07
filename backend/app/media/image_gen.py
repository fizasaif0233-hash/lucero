"""Image generation via Replicate FLUX → SDXL fallback + image tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.media.replicate_client import ReplicateClient, ReplicateError
from app.media.storage import GeneratedStorage
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ImageGenError(Exception):
    """Raised when image generation cannot be fulfilled."""


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
        return self._client.enabled

    @property
    def gemini_enabled(self) -> bool:
        # Kept for callers; Gemini image path is intentionally disabled.
        return False

    async def generate(
        self,
        *,
        user_id: str,
        prompt: str,
        aspect: str = "3:4",
        title: str = "Generated image",
    ) -> Dict[str, Any]:
        if not self._client.enabled:
            raise ImageGenError(
                "REPLICATE_API_TOKEN is not set. Add it on Railway to generate images."
            )
        try:
            return await self._generate_replicate(
                user_id=user_id, prompt=prompt, aspect=aspect, title=title
            )
        except Exception as exc:
            raise ImageGenError(str(exc)) from exc

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
