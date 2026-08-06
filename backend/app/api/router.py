from fastapi import APIRouter

from app.api import agents, automation, channels, chat, documents, memory

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(chat.router)
api_router.include_router(documents.router)
api_router.include_router(memory.router)
api_router.include_router(automation.router)
api_router.include_router(agents.router)
api_router.include_router(channels.router)
