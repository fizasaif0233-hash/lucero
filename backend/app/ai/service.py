from typing import AsyncIterator, Dict, List, Optional

from app.ai.base import AIProvider
from app.ai.openrouter import OpenRouterProvider
from app.ai.prompts import build_system_prompt
from app.core.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AIService:
    """
    Application AI facade.

    Responsibilities:
    - Attach L.U.C.E.R.O system prompt (+ RAG context)
    - Delegate chat/embeddings to an injectable provider
    """

    def __init__(
        self,
        provider: AIProvider,
        settings: Optional[Settings] = None,
    ) -> None:
        self._provider = provider
        self._settings = settings or get_settings()

    @property
    def default_model(self) -> str:
        return self._settings.openrouter_default_model

    async def stream_response(
        self,
        user_messages: List[Dict[str, str]],
        *,
        knowledge_context: Optional[str] = None,
        specialist_overlay: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.4,
    ) -> AsyncIterator[str]:
        messages = self._with_system(
            user_messages,
            knowledge_context,
            specialist_overlay=specialist_overlay,
        )
        primary = model or self.default_model
        fallback = self._settings.openrouter_fallback_model
        models = [primary]
        if fallback and fallback != primary:
            models.append(fallback)

        last_error: Optional[Exception] = None
        for attempt_model in models:
            logger.info(
                "ai_stream_start",
                model=attempt_model,
                message_count=len(messages),
                has_rag=bool(knowledge_context),
                has_specialist=bool(specialist_overlay),
            )
            try:
                async for token in self._provider.stream_chat(
                    messages, model=attempt_model, temperature=temperature
                ):
                    yield token
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "ai_stream_model_failed",
                    model=attempt_model,
                    error=str(exc),
                )
        if last_error:
            raise last_error

    async def complete_response(
        self,
        user_messages: List[Dict[str, str]],
        *,
        knowledge_context: Optional[str] = None,
        specialist_overlay: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.4,
    ) -> str:
        messages = self._with_system(
            user_messages,
            knowledge_context,
            specialist_overlay=specialist_overlay,
        )
        primary = model or self.default_model
        fallback = self._settings.openrouter_fallback_model
        for attempt_model in [primary, fallback]:
            if not attempt_model:
                continue
            try:
                return await self._provider.complete_chat(
                    messages, model=attempt_model, temperature=temperature
                )
            except Exception as exc:
                logger.warning(
                    "ai_complete_model_failed",
                    model=attempt_model,
                    error=str(exc),
                )
        return ""

    async def complete_task(
        self,
        instruction: str,
        user_content: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.35,
    ) -> str:
        """Structured automation tasks — JSON/tool style, no long brand system prompt."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are L.U.C.E.R.O automation. Follow the instruction exactly. "
                    "When asked for JSON, return ONLY valid JSON with no markdown fences."
                ),
            },
            {
                "role": "user",
                "content": f"{instruction.strip()}\n\n{user_content.strip()}",
            },
        ]
        return await self._provider.complete_chat(
            messages, model=model, temperature=temperature
        )

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return await self._provider.embed(texts)

    @staticmethod
    def _with_system(
        user_messages: List[Dict[str, str]],
        knowledge_context: Optional[str],
        specialist_overlay: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        system = build_system_prompt(
            knowledge_context, specialist_overlay=specialist_overlay
        )
        return [{"role": "system", "content": system}, *user_messages]


def create_ai_service(settings: Optional[Settings] = None) -> AIService:
    """Factory for dependency injection."""
    cfg = settings or get_settings()
    provider = OpenRouterProvider(cfg)
    return AIService(provider=provider, settings=cfg)
