from fastapi import APIRouter

from app.api import (
    agents,
    automation,
    bookings,
    calendar_api,
    channels,
    chat,
    crm,
    documents,
    email,
    memory,
    os_api,
    reminders,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(chat.router)
api_router.include_router(documents.router)
api_router.include_router(memory.router)
api_router.include_router(automation.router)
api_router.include_router(agents.router)
api_router.include_router(channels.router)
api_router.include_router(email.router)
api_router.include_router(bookings.router)
api_router.include_router(calendar_api.router)
api_router.include_router(reminders.router)
api_router.include_router(crm.router)
api_router.include_router(os_api.router)
