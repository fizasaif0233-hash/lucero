"""Thin Replicate HTTP client (predictions API)."""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, Optional

import httpx

from app.core.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

REPLICATE_API = "https://api.replicate.com/v1"


class ReplicateError(RuntimeError):
    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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

    @staticmethod
    def _retry_after_seconds(resp: httpx.Response, fallback: float = 12.0) -> float:
        # Header first
        hdr = resp.headers.get("retry-after")
        if hdr:
            try:
                return max(1.0, float(hdr))
            except ValueError:
                pass
        # JSON body: "retry_after": 10 or "resets in ~10s"
        try:
            body = resp.json()
            if isinstance(body, dict):
                if body.get("retry_after") is not None:
                    return max(1.0, float(body["retry_after"]))
                detail = str(body.get("detail") or "")
                m = re.search(r"resets in\s*~?(\d+)\s*s", detail, re.I)
                if m:
                    return max(1.0, float(m.group(1)))
        except Exception:
            pass
        text = resp.text or ""
        m = re.search(r"resets in\s*~?(\d+)\s*s", text, re.I)
        if m:
            return max(1.0, float(m.group(1)))
        return fallback

    async def _create_prediction(
        self,
        client: httpx.AsyncClient,
        model: str,
        input_payload: Dict[str, Any],
        *,
        max_retries: int = 5,
    ) -> dict:
        last_text = ""
        for attempt in range(max_retries):
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
            if create.status_code == 429:
                wait_s = self._retry_after_seconds(create) + 1.0
                last_text = create.text[:500]
                logger.warning(
                    "replicate_rate_limited",
                    attempt=attempt + 1,
                    wait_s=wait_s,
                )
                await asyncio.sleep(wait_s)
                continue
            if create.status_code >= 400:
                raise ReplicateError(
                    f"Replicate create failed ({create.status_code}): {create.text[:500]}",
                    status_code=create.status_code,
                )
            return create.json()

        raise ReplicateError(
            "Replicate rate limit (429): too many predictions. "
            "Wait ~15s and try again, or add a payment method on replicate.com "
            f"to raise the limit. Last response: {last_text}",
            status_code=429,
        )

    async def run(
        self,
        model: str,
        input_payload: Dict[str, Any],
        *,
        timeout_s: float = 300.0,
        poll_s: float = 2.0,
    ) -> Any:
        """Create a prediction and wait until succeeded/failed."""
        async with httpx.AsyncClient(timeout=90.0) as client:
            prediction = await self._create_prediction(
                client, model, input_payload
            )
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
                if resp.status_code == 429:
                    await asyncio.sleep(self._retry_after_seconds(resp))
                    continue
                if resp.status_code >= 400:
                    raise ReplicateError(
                        f"Replicate poll failed ({resp.status_code}): {resp.text[:300]}",
                        status_code=resp.status_code,
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
