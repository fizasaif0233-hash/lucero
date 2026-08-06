from typing import List, Optional
from uuid import UUID

from app.database.client import get_supabase_admin
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ConversationRepository:
    def __init__(self) -> None:
        self._db = get_supabase_admin()

    def list_for_user(self, user_id: str | UUID) -> List[dict]:
        result = (
            self._db.table("conversations")
            .select("*")
            .eq("user_id", str(user_id))
            .order("updated_at", desc=True)
            .execute()
        )
        return result.data or []

    def get(self, conversation_id: str | UUID, user_id: str | UUID) -> Optional[dict]:
        result = (
            self._db.table("conversations")
            .select("*")
            .eq("id", str(conversation_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def create(
        self,
        user_id: str | UUID,
        title: str = "New conversation",
        model: Optional[str] = None,
    ) -> dict:
        result = (
            self._db.table("conversations")
            .insert(
                {
                    "user_id": str(user_id),
                    "title": title,
                    "model": model,
                }
            )
            .execute()
        )
        return result.data[0]

    def update_title(self, conversation_id: str | UUID, title: str) -> dict:
        result = (
            self._db.table("conversations")
            .update({"title": title[:120]})
            .eq("id", str(conversation_id))
            .execute()
        )
        return result.data[0]

    def touch(self, conversation_id: str | UUID) -> None:
        # Force updated_at via trigger by re-writing title
        result = (
            self._db.table("conversations")
            .select("title")
            .eq("id", str(conversation_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            return
        self._db.table("conversations").update(
            {"title": result.data[0]["title"]}
        ).eq("id", str(conversation_id)).execute()

    def delete(self, conversation_id: str | UUID, user_id: str | UUID) -> bool:
        existing = self.get(conversation_id, user_id)
        if not existing:
            return False
        self._db.table("conversations").delete().eq(
            "id", str(conversation_id)
        ).execute()
        return True


class MessageRepository:
    def __init__(self) -> None:
        self._db = get_supabase_admin()

    def list_for_conversation(self, conversation_id: str | UUID) -> List[dict]:
        result = (
            self._db.table("messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []

    def create(
        self,
        *,
        conversation_id: str | UUID,
        role: str,
        content: str,
        model: Optional[str] = None,
    ) -> dict:
        result = (
            self._db.table("messages")
            .insert(
                {
                    "conversation_id": str(conversation_id),
                    "role": role,
                    "content": content,
                    "model": model,
                }
            )
            .execute()
        )
        return result.data[0]

    def delete(self, message_id: str | UUID) -> None:
        self._db.table("messages").delete().eq("id", str(message_id)).execute()

    def get(self, message_id: str | UUID) -> Optional[dict]:
        result = (
            self._db.table("messages")
            .select("*")
            .eq("id", str(message_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def delete_after(self, conversation_id: str | UUID, created_at: str) -> None:
        """Delete messages at/after timestamp (for regenerate)."""
        self._db.table("messages").delete().eq(
            "conversation_id", str(conversation_id)
        ).gte("created_at", created_at).execute()


class DocumentRepository:
    def __init__(self) -> None:
        self._db = get_supabase_admin()

    def list_for_user(self, user_id: str | UUID) -> List[dict]:
        result = (
            self._db.table("business_documents")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def get(self, document_id: str | UUID, user_id: str | UUID) -> Optional[dict]:
        result = (
            self._db.table("business_documents")
            .select("*")
            .eq("id", str(document_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def delete(self, document_id: str | UUID, user_id: str | UUID) -> bool:
        doc = self.get(document_id, user_id)
        if not doc:
            return False
        # Chunks cascade via FK
        self._db.table("business_documents").delete().eq(
            "id", str(document_id)
        ).execute()
        return True


class MemoryRepository:
    def __init__(self) -> None:
        self._db = get_supabase_admin()

    def list_for_user(self, user_id: str | UUID) -> List[dict]:
        result = (
            self._db.table("memory")
            .select("*")
            .eq("user_id", str(user_id))
            .order("updated_at", desc=True)
            .execute()
        )
        return result.data or []

    def create(
        self,
        *,
        user_id: str | UUID,
        content: str,
        key: Optional[str] = None,
        category: str = "general",
        embedding: Optional[List[float]] = None,
    ) -> dict:
        payload = {
            "user_id": str(user_id),
            "content": content,
            "key": key,
            "category": category,
        }
        if embedding is not None:
            payload["embedding"] = embedding
        result = self._db.table("memory").insert(payload).execute()
        return result.data[0]

    def delete(self, memory_id: str | UUID, user_id: str | UUID) -> bool:
        result = (
            self._db.table("memory")
            .delete()
            .eq("id", str(memory_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return bool(result.data)


class ChannelIdentityRepository:
    def __init__(self) -> None:
        self._db = get_supabase_admin()

    def get_by_external(
        self, channel: str, external_id: str
    ) -> Optional[dict]:
        normalized = _normalize_external_id(external_id)
        result = (
            self._db.table("channel_identities")
            .select("*")
            .eq("channel", channel)
            .eq("external_id", normalized)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        # Also try raw id (JID forms)
        if normalized != external_id:
            result = (
                self._db.table("channel_identities")
                .select("*")
                .eq("channel", channel)
                .eq("external_id", external_id.strip())
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]
        return None

    def list_for_channel(self, channel: Optional[str] = None) -> List[dict]:
        query = self._db.table("channel_identities").select("*")
        if channel:
            query = query.eq("channel", channel)
        result = query.order("created_at", desc=False).execute()
        return result.data or []

    def list_allowed(self, channel: Optional[str] = None) -> List[dict]:
        rows = self.list_for_channel(channel)
        return [r for r in rows if r.get("allowed")]

    def touch_message(self, identity_id: str | UUID) -> None:
        from datetime import datetime, timezone

        self._db.table("channel_identities").update(
            {"last_message_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", str(identity_id)).execute()


class ChannelGatewayStatusRepository:
    def __init__(self) -> None:
        self._db = get_supabase_admin()

    def get(self) -> Optional[dict]:
        result = (
            self._db.table("channel_gateway_status")
            .select("*")
            .eq("id", "default")
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def upsert(
        self,
        *,
        online: Optional[bool] = None,
        whatsapp_linked: Optional[bool] = None,
        last_external_id: Optional[str] = None,
        meta: Optional[dict] = None,
        heartbeat: bool = False,
        message: bool = False,
    ) -> dict:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        existing = self.get() or {"id": "default", "meta": {}}
        payload: dict = {"id": "default", "updated_at": now}
        for key in (
            "online",
            "whatsapp_linked",
            "last_heartbeat_at",
            "last_message_at",
            "last_external_id",
            "meta",
        ):
            if key in existing and key not in payload:
                payload[key] = existing[key]
        if online is not None:
            payload["online"] = online
        if whatsapp_linked is not None:
            payload["whatsapp_linked"] = whatsapp_linked
        if last_external_id is not None:
            payload["last_external_id"] = last_external_id
        if meta is not None:
            payload["meta"] = meta
        if heartbeat:
            payload["last_heartbeat_at"] = now
            payload["online"] = True
        if message:
            payload["last_message_at"] = now
        result = (
            self._db.table("channel_gateway_status")
            .upsert(payload, on_conflict="id")
            .execute()
        )
        return result.data[0] if result.data else payload


def _normalize_external_id(external_id: str) -> str:
    """Normalize phone / JID to a stable allowlist key."""
    raw = (external_id or "").strip()
    if not raw:
        return raw
    # WhatsApp JIDs: 15551234567@s.whatsapp.net
    if "@" in raw:
        raw = raw.split("@", 1)[0]
    digits = "".join(c for c in raw if c.isdigit())
    if digits and (raw.startswith("+") or len(digits) >= 10):
        return f"+{digits}" if not raw.startswith("+") else f"+{digits}"
    if digits and len(digits) >= 8:
        return f"+{digits}"
    return raw
