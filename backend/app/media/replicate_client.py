"""Thin Replicate HTTP client (predictions API)."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx

from app.core.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

REPLICATE_API = "https://api.replicate.com/v1"


class ReplicateError(RuntimeError):
    pass


class ReplicateClient:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool((self._settings.replicate_api_token or "").strip())

    def _headers(self) -> Dict[str, str]:
        token = (self._settings.replicate_api_token or "").strip()
        if not token:
            raise ReplicateError(
                "REPLICATE_API_TOKEN is not configured — media generation unavailable."
            )
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }

    async def run(
        self,
        model: str,
        input_payload: Dict[str, Any],
        *,
        timeout_s: float = 300.0,
        poll_s: float = 2.0,
    ) -> Any:
        """Create a prediction and wait until succeeded/failed."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            create = await client.post(
                f"{REPLICATE_API}/models/{model}/predictions",
                headers=self._headers(),
                json={"input": input_payload},
            )
            if create.status_code >= 400:
                create = await client.post(
                    f"{REPLICATE_API}/predictions",
                    headers=self._headers(),
                    json={"model": model, "input": input_payload},
                )
            if create.status_code >= 400:
                raise ReplicateError(
                    f"Replicate create failed ({create.status_code}): {create.text[:500]}"
                )

            prediction = create.json()
            status = prediction.get("status")
            if status in {"succeeded", "failed", "canceled"}:
                if status != "succeeded":
                    raise ReplicateError(
                        prediction.get("error")
                        or f"Replicate prediction {status}"
                    )
                return prediction.get("output")

            url = prediction.get("urls", {}).get("get") or (
                f"{REPLICATE_API}/predictions/{prediction.get('id')}"
            )
            loop = asyncio.get_event_loop()
            deadline = loop.time() + timeout_s
            while loop.time() < deadline:
                await asyncio.sleep(poll_s)
                resp = await client.get(url, headers=self._headers())
                if resp.status_code >= 400:
                    raise ReplicateError(
                        f"Replicate poll failed ({resp.status_code}): {resp.text[:300]}"
                    )
                prediction = resp.json()
                status = prediction.get("status")
                if status == "succeeded":
                    return prediction.get("output")
                if status in {"failed", "canceled"}:
                    raise ReplicateError(
                        prediction.get("error")
                        or f"Replicate prediction {status}"
                    )
            raise ReplicateError("Replicate prediction timed out")
