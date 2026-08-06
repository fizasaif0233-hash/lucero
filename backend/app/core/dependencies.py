from functools import lru_cache

from fastapi import Depends

from app.ai.service import AIService, create_ai_service
from app.core.config import Settings, get_settings
from app.rag.ingestion import IngestionService
from app.rag.retriever import Retriever
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService, HistoryService, MemoryService
from app.automation.service import AutomationService
from app.agents.orchestrator import AgentOrchestrator


@lru_cache
def get_ai_service() -> AIService:
    return create_ai_service(get_settings())


def get_retriever(
    ai: AIService = Depends(get_ai_service),
    settings: Settings = Depends(get_settings),
) -> Retriever:
    return Retriever(ai_service=ai, settings=settings)


def get_ingestion_service(
    ai: AIService = Depends(get_ai_service),
    settings: Settings = Depends(get_settings),
) -> IngestionService:
    return IngestionService(ai_service=ai, settings=settings)


def get_chat_service(
    ai: AIService = Depends(get_ai_service),
    retriever: Retriever = Depends(get_retriever),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    return ChatService(ai_service=ai, retriever=retriever, settings=settings)


def get_document_service(
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> DocumentService:
    return DocumentService(ingestion=ingestion)


def get_history_service() -> HistoryService:
    return HistoryService()


def get_memory_service(
    ai: AIService = Depends(get_ai_service),
) -> MemoryService:
    return MemoryService(ai_service=ai)


def get_automation_service(
    ai: AIService = Depends(get_ai_service),
    retriever: Retriever = Depends(get_retriever),
) -> AutomationService:
    return AutomationService(ai_service=ai, retriever=retriever)


def get_agent_orchestrator(
    ai: AIService = Depends(get_ai_service),
    retriever: Retriever = Depends(get_retriever),
) -> AgentOrchestrator:
    return AgentOrchestrator(ai=ai, retriever=retriever)
