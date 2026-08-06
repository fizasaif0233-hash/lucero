from typing import List, Optional
from uuid import UUID

from app.ai.service import AIService
from app.database.repositories import DocumentRepository
from app.rag.ingestion import IngestionService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DocumentService:
    def __init__(
        self,
        ingestion: IngestionService,
        documents: Optional[DocumentRepository] = None,
    ) -> None:
        self._ingestion = ingestion
        self._documents = documents or DocumentRepository()

    async def upload(
        self, *, user_id: str | UUID, filename: str, file_bytes: bytes
    ) -> dict:
        return await self._ingestion.ingest_upload(
            user_id=user_id,
            filename=filename,
            file_bytes=file_bytes,
        )

    def list_documents(self, user_id: str | UUID) -> List[dict]:
        return self._documents.list_for_user(user_id)

    def delete_document(self, document_id: str | UUID, user_id: str | UUID) -> bool:
        return self._documents.delete(document_id, user_id)


class HistoryService:
    def __init__(
        self,
        conversations=None,
        messages=None,
    ) -> None:
        from app.database.repositories import ConversationRepository, MessageRepository

        self._conversations = conversations or ConversationRepository()
        self._messages = messages or MessageRepository()

    def list_conversations(self, user_id: str | UUID) -> List[dict]:
        return self._conversations.list_for_user(user_id)

    def get_conversation(
        self, conversation_id: str | UUID, user_id: str | UUID
    ) -> Optional[dict]:
        conversation = self._conversations.get(conversation_id, user_id)
        if not conversation:
            return None
        msgs = self._messages.list_for_conversation(conversation_id)
        return {**conversation, "messages": msgs}

    def delete_conversation(
        self, conversation_id: str | UUID, user_id: str | UUID
    ) -> bool:
        return self._conversations.delete(conversation_id, user_id)


class MemoryService:
    def __init__(self, ai_service: AIService, memories=None) -> None:
        from app.database.repositories import MemoryRepository

        self._ai = ai_service
        self._memories = memories or MemoryRepository()

    def list_memory(self, user_id: str | UUID) -> List[dict]:
        return self._memories.list_for_user(user_id)

    async def create_memory(
        self,
        *,
        user_id: str | UUID,
        content: str,
        key: Optional[str] = None,
        category: str = "general",
    ) -> dict:
        vectors = await self._ai.embed_texts([content])
        embedding = vectors[0] if vectors else None
        return self._memories.create(
            user_id=user_id,
            content=content,
            key=key,
            category=category,
            embedding=embedding,
        )

    def delete_memory(self, memory_id: str | UUID, user_id: str | UUID) -> bool:
        return self._memories.delete(memory_id, user_id)
