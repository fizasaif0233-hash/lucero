from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional


class AIProvider(ABC):
    """Abstract AI provider — swap OpenRouter for another backend later."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.4,
    ) -> AsyncIterator[str]:
        """Yield assistant text tokens."""

    @abstractmethod
    async def complete_chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.4,
    ) -> str:
        """Return a full assistant response."""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Return embedding vectors for each input text."""
