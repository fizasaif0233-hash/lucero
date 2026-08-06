from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.base import AIProvider
from app.core.config import Settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OpenRouterProvider(AIProvider):
    """OpenRouter chat + embeddings client."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://jarvis.local",
            "X-Title": settings.app_name,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def complete_chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.4,
    ) -> str:
        payload = {
            "model": model or self._settings.openrouter_default_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("unexpected_openrouter_response", data=data)
            raise RuntimeError("Malformed OpenRouter response") from exc

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.4,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model or self._settings.openrouter_default_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        token = self._parse_stream_chunk(data)
                        if token:
                            yield token

    @staticmethod
    def _parse_stream_chunk(data: str) -> Optional[str]:
        import orjson

        try:
            parsed: Dict[str, Any] = orjson.loads(data)
            delta = parsed["choices"][0].get("delta") or {}
            content = delta.get("content")
            return content if isinstance(content, str) else None
        except Exception:
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # Batch to stay within provider limits
        batch_size = 64
        vectors: List[List[float]] = []
        async with httpx.AsyncClient(timeout=120.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                payload = {
                    "model": self._settings.openrouter_embedding_model,
                    "input": batch,
                }
                response = await client.post(
                    f"{self._base_url}/embeddings",
                    headers=self._headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                ordered = sorted(data["data"], key=lambda item: item["index"])
                vectors.extend([item["embedding"] for item in ordered])
        return vectors
