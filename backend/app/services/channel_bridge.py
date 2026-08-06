"""OpenAI-compatible channel bridge used by ZeroClaw (WhatsApp transport)."""

from __future__ import annotations

import re
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from app.core.config import Settings, get_settings
from app.database.repositories import (
    ChannelGatewayStatusRepository,
    ChannelIdentityRepository,
)
from app.services.chat_service import ChatService
from app.utils.logging import get_logger

logger = get_logger(__name__)

_PHONE_RE = re.compile(
    r"(?:\+\d{8,15}\b)|(?:\d{10,15}@s\.whatsapp\.net)",
    re.IGNORECASE,
)


def _looks_like_e164(value: str) -> bool:
    """True only for real WhatsApp phone forms — not LIDs, dates, or session junk."""
    raw = (value or "").strip()
    if not raw:
        return False
    if "@s.whatsapp.net" in raw.lower():
        user = raw.split("@", 1)[0]
        digits = "".join(c for c in user if c.isdigit())
        return 10 <= len(digits) <= 15
    # Require explicit +E.164. Bare digit strings are often LIDs / timestamps.
    if not raw.startswith("+"):
        return False
    digits = "".join(c for c in raw if c.isdigit())
    return 8 <= len(digits) <= 15


class ChannelBridgeService:
    """Map ZeroClaw / OpenAI chat requests onto L.U.C.E.R.O agents + RAG."""

    def __init__(
        self,
        chat_service: ChatService,
        settings: Optional[Settings] = None,
        identities: Optional[ChannelIdentityRepository] = None,
        gateway: Optional[ChannelGatewayStatusRepository] = None,
    ) -> None:
        self._chat = chat_service
        self._settings = settings or get_settings()
        self._identities = identities or ChannelIdentityRepository()
        self._gateway = gateway or ChannelGatewayStatusRepository()

    @staticmethod
    def _normalize_phone(value: str) -> str:
        from app.database.repositories import _normalize_external_id

        return _normalize_external_id(value)

    def _env_allowlist(self) -> List[str]:
        return [
            self._normalize_phone(n)
            for n in self._settings.channel_allowed_number_list
            if n
        ]

    def _is_env_allowed(self, candidate: str) -> bool:
        allow = self._env_allowlist()
        if not allow:
            return True
        return self._normalize_phone(candidate) in allow

    def resolve_identity(
        self,
        *,
        channel: str,
        external_id: Optional[str],
        user_hint: Optional[str] = None,
    ) -> Tuple[Optional[dict], Optional[str]]:
        """
        Returns (identity_row | None, deny_reason | None).
        If both None and external_id missing, fall back to default user
        only when CHANNEL_ALLOWED_NUMBERS is empty.
        """
        candidate = (external_id or user_hint or "").strip() or None
        if candidate and not _looks_like_e164(candidate):
            # ZeroClaw often sends LIDs / dates / session ids in `user`.
            logger.info(
                "channel_ignore_non_phone_id",
                channel=channel,
                external_id=candidate,
            )
            candidate = None
        if candidate:
            candidate = self._normalize_phone(candidate)
            # Soft env allowlist: only deny clear +E.164 phones that are not
            # listed. Never deny the linked bot number or unknown formats.
            allow = self._env_allowlist()
            if (
                allow
                and candidate.startswith("+")
                and 8 <= len("".join(c for c in candidate if c.isdigit())) <= 15
                and candidate not in allow
            ):
                # If ZeroClaw attributed the bot's own pair_phone, treat as allowed.
                bot = (getattr(self._settings, "channel_bot_phone", None) or "").strip()
                bot_n = self._normalize_phone(bot) if bot else ""
                if candidate != bot_n:
                    logger.info(
                        "channel_env_allowlist_miss",
                        channel=channel,
                        external_id=candidate,
                        allow=allow,
                    )
                    # Map to default owner instead of hard-deny — WhatsApp often
                    # mis-labels sender as bot/LID while peer-gate already passed.
                    if self._settings.channel_default_user_id:
                        return (
                            {
                                "user_id": self._settings.channel_default_user_id,
                                "is_owner": True,
                                "allowed": True,
                                "external_id": allow[0],
                                "channel": channel,
                            },
                            None,
                        )
                    return (
                        {
                            "external_id": candidate,
                            "channel": channel,
                            "allowed": False,
                        },
                        "denied",
                    )
            try:
                row = self._identities.get_by_external(channel, candidate)
            except Exception as exc:
                logger.warning(
                    "channel_identity_lookup_failed",
                    error=str(exc),
                    channel=channel,
                )
                if self._settings.channel_default_user_id:
                    return (
                        {
                            "user_id": self._settings.channel_default_user_id,
                            "is_owner": True,
                            "allowed": True,
                            "external_id": candidate,
                            "channel": channel,
                        },
                        None,
                    )
                return None, "unknown"
            if row is None:
                if self._settings.channel_default_user_id:
                    return (
                        {
                            "user_id": self._settings.channel_default_user_id,
                            "is_owner": True,
                            "allowed": True,
                            "external_id": candidate,
                            "channel": channel,
                        },
                        None,
                    )
                return None, "unknown"
            if not row.get("allowed"):
                # Prefer env/default over a stale denied DB row for the owner phone.
                if allow and candidate in allow and self._settings.channel_default_user_id:
                    return (
                        {
                            "user_id": self._settings.channel_default_user_id,
                            "is_owner": True,
                            "allowed": True,
                            "external_id": candidate,
                            "channel": channel,
                        },
                        None,
                    )
                return row, "denied"
            return row, None

        # No usable phone. With a configured allowlist, ZeroClaw peer-gates
        # senders — map to the allowlisted owner identity / default user.
        allow = self._env_allowlist()
        if allow and self._settings.channel_default_user_id:
            return (
                {
                    "user_id": self._settings.channel_default_user_id,
                    "is_owner": True,
                    "allowed": True,
                    "external_id": allow[0],
                    "channel": channel,
                },
                None,
            )

        # No phone provided — use configured service user if set
        if self._settings.channel_default_user_id:
            return (
                {
                    "user_id": self._settings.channel_default_user_id,
                    "is_owner": True,
                    "allowed": True,
                    "external_id": "default",
                    "channel": channel,
                },
                None,
            )
        # Dev convenience: first owner/wife profile when allowlist not ready
        if self._settings.is_development:
            owner = self._first_app_user()
            if owner:
                return (
                    {
                        "user_id": owner,
                        "is_owner": True,
                        "allowed": True,
                        "external_id": "dev-default",
                        "channel": channel,
                    },
                    None,
                )
        return None, "missing_identity"

    @staticmethod
    def _first_app_user() -> Optional[str]:
        try:
            from app.database.client import get_supabase_admin

            db = get_supabase_admin()
            result = (
                db.table("users")
                .select("id")
                .order("created_at", desc=False)
                .limit(1)
                .execute()
            )
            if result.data:
                return str(result.data[0]["id"])
        except Exception:
            logger.warning("channel_default_user_lookup_failed")
        return None

    def agent_for_identity(self, identity: Optional[dict]) -> Optional[str]:
        """Owners get full router; others default to Support Agent."""
        if identity and identity.get("is_owner"):
            return None
        default = (self._settings.channel_default_agent or "support").strip()
        return default or "support"

    def extract_user_message(self, messages: List[dict]) -> str:
        parts: List[str] = []
        for m in messages:
            role = (m.get("role") or "").lower()
            if role != "user":
                continue
            content = m.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(str(block.get("text") or ""))
                    elif isinstance(block, str):
                        parts.append(block)
        return "\n".join(p for p in parts if p).strip()

    @staticmethod
    def guess_external_id(
        *,
        body_user: Optional[str],
        header_external_id: Optional[str],
        message_text: str,
    ) -> Optional[str]:
        for raw in (header_external_id, body_user):
            if not raw:
                continue
            candidate = raw.strip()
            if _looks_like_e164(candidate):
                return candidate
        match = _PHONE_RE.search(message_text or "")
        if match:
            return match.group(0).strip()
        return None

    async def complete(
        self,
        *,
        messages: List[dict],
        channel: str = "whatsapp",
        external_id: Optional[str] = None,
        body_user: Optional[str] = None,
        model: Optional[str] = None,
        force_agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        text = self.extract_user_message(messages)
        if not text:
            return self._openai_message(
                "I did not receive a message. Please try again.",
                model=model,
            )

        guessed = self.guess_external_id(
            body_user=body_user,
            header_external_id=external_id,
            message_text=text,
        )
        identity, deny = self.resolve_identity(
            channel=channel, external_id=guessed, user_hint=None
        )
        if deny:
            logger.info(
                "channel_denied",
                channel=channel,
                external_id=guessed,
                reason=deny,
            )
            return self._openai_message(
                self._settings.channel_deny_message,
                model=model,
            )

        assert identity is not None
        user_id = identity["user_id"]
        agent_id = (
            force_agent_id
            if force_agent_id is not None
            else self.agent_for_identity(identity)
        )
        selected_model = self._resolve_model(model)

        if identity.get("id"):
            try:
                self._identities.touch_message(identity["id"])
            except Exception:
                pass
        try:
            self._gateway.upsert(
                message=True,
                last_external_id=guessed or identity.get("external_id"),
                online=True,
            )
        except Exception:
            logger.warning("channel_gateway_touch_failed")

        content = await self._run_chat(
            user_id=user_id,
            message=text,
            model=selected_model,
            agent_id=agent_id,
        )
        return self._openai_message(content, model=model or "lucero/agents")

    def _resolve_model(self, model: Optional[str]) -> Optional[str]:
        """Map ZeroClaw model ids onto OpenRouter / L.U.C.E.R.O models."""
        if not model:
            return None
        lowered = model.strip().lower()
        if lowered in {"lucero/agents", "lucero", "jarvis", "channel"}:
            return None  # ChatService uses AIService.default_model
        return model

    async def stream(
        self,
        *,
        messages: List[dict],
        channel: str = "whatsapp",
        external_id: Optional[str] = None,
        body_user: Optional[str] = None,
        model: Optional[str] = None,
        force_agent_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Yield OpenAI SSE chunk lines (data: ...)."""
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())
        selected_model = model or "lucero/agents"

        text = self.extract_user_message(messages)
        if not text:
            async for line in self._stream_text(
                completion_id, created, selected_model, "Empty message."
            ):
                yield line
            return

        guessed = self.guess_external_id(
            body_user=body_user,
            header_external_id=external_id,
            message_text=text,
        )
        identity, deny = self.resolve_identity(
            channel=channel, external_id=guessed, user_hint=None
        )
        if deny:
            async for line in self._stream_text(
                completion_id,
                created,
                selected_model,
                self._settings.channel_deny_message,
            ):
                yield line
            return

        assert identity is not None
        user_id = identity["user_id"]
        agent_id = (
            force_agent_id
            if force_agent_id is not None
            else self.agent_for_identity(identity)
        )
        selected_model = self._resolve_model(model)

        try:
            self._gateway.upsert(
                message=True,
                last_external_id=guessed or identity.get("external_id"),
                online=True,
            )
        except Exception:
            pass

        # Role opener
        import orjson

        opener = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": selected_model or "lucero/agents",
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant"},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {orjson.dumps(opener).decode()}\n\n"

        async for event in self._chat.stream_chat(
            user_id=user_id,
            message=text,
            model=selected_model,
            agent_id=agent_id,
        ):
            if event.get("event") != "token":
                continue
            raw = event.get("data") or ""
            try:
                token = orjson.loads(raw) if raw.startswith('"') else raw
            except Exception:
                token = raw
            if not token:
                continue
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": selected_model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": token},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {orjson.dumps(chunk).decode()}\n\n"

        done = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": selected_model,
            "choices": [
                {"index": 0, "delta": {}, "finish_reason": "stop"}
            ],
        }
        yield f"data: {orjson.dumps(done).decode()}\n\n"
        yield "data: [DONE]\n\n"

    async def _run_chat(
        self,
        *,
        user_id: str,
        message: str,
        model: Optional[str],
        agent_id: Optional[str],
    ) -> str:
        import orjson

        pieces: List[str] = []
        final = ""
        async for event in self._chat.stream_chat(
            user_id=user_id,
            message=message,
            model=model,
            agent_id=agent_id,
        ):
            etype = event.get("event")
            if etype == "token":
                raw = event.get("data") or ""
                try:
                    token = orjson.loads(raw) if raw.startswith('"') else raw
                except Exception:
                    token = raw
                pieces.append(str(token))
            elif etype == "done":
                try:
                    payload = orjson.loads(event.get("data") or "{}")
                    final = payload.get("content") or ""
                except Exception:
                    pass
            elif etype == "error":
                return f"L.U.C.E.R.O error: {event.get('data')}"
        return (final or "".join(pieces)).strip() or (
            "I was unable to generate a response. Please try again."
        )

    def _openai_message(
        self, content: str, *, model: Optional[str]
    ) -> Dict[str, Any]:
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model or "lucero/agents",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    async def _stream_text(
        self,
        completion_id: str,
        created: int,
        model: str,
        text: str,
    ) -> AsyncIterator[str]:
        import orjson

        opener = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": text},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {orjson.dumps(opener).decode()}\n\n"
        done = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {"index": 0, "delta": {}, "finish_reason": "stop"}
            ],
        }
        yield f"data: {orjson.dumps(done).decode()}\n\n"
        yield "data: [DONE]\n\n"
