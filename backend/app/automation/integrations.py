"""Future-ready integration interfaces (stubs until credentials exist)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OutboundEmail:
    to: str
    subject: str
    body: str
    to_name: Optional[str] = None


@dataclass
class CalendarEventPayload:
    title: str
    starts_at: str
    ends_at: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    guests: Optional[List[str]] = None


class EmailService(ABC):
    """Replace StubEmailService with SMTP / Gmail / SendGrid later."""

    @abstractmethod
    async def send(self, message: OutboundEmail) -> Dict[str, Any]:
        raise NotImplementedError


class CalendarService(ABC):
    """Replace StubCalendarService with Google Calendar later."""

    @abstractmethod
    async def create_event(self, event: CalendarEventPayload) -> Dict[str, Any]:
        raise NotImplementedError


class MessagingService(ABC):
    """WhatsApp / Telegram / Slack future adapters."""

    @abstractmethod
    async def send_message(self, channel: str, to: str, body: str) -> Dict[str, Any]:
        raise NotImplementedError


class StubEmailService(EmailService):
    async def send(self, message: OutboundEmail) -> Dict[str, Any]:
        return {
            "status": "queued_local",
            "provider": "stub",
            "to": message.to,
            "subject": message.subject,
            "note": "Email provider not connected — draft saved only.",
        }


def get_email_service() -> EmailService:
    """Prefer Resend when configured; otherwise stub."""
    from app.core.config import get_settings
    from app.services.lucero_email import ResendEmailService

    settings = get_settings()
    resend = ResendEmailService(settings)
    if resend.configured:
        return resend
    return StubEmailService()


class StubCalendarService(CalendarService):
    async def create_event(self, event: CalendarEventPayload) -> Dict[str, Any]:
        return {
            "status": "stored_local",
            "provider": "lucero_postgres",
            "id": f"lucero-{event.starts_at}",
            "title": event.title,
            "starts_at": event.starts_at,
            "note": "Saved to L.U.C.E.R.O internal calendar (PostgreSQL).",
        }


class InternalCalendarService(CalendarService):
    """Bookings live in PostgreSQL — no Google Calendar."""

    async def create_event(self, event: CalendarEventPayload) -> Dict[str, Any]:
        return {
            "status": "stored_local",
            "provider": "lucero_postgres",
            "id": f"lucero-{event.title}-{event.starts_at}",
            "title": event.title,
            "starts_at": event.starts_at,
            "note": "Internal calendar event recorded with booking.",
        }


class StubMessagingService(MessagingService):
    async def send_message(self, channel: str, to: str, body: str) -> Dict[str, Any]:
        return {
            "status": "queued_local",
            "provider": "stub",
            "channel": channel,
            "to": to,
            "note": f"{channel} not connected — reply saved as draft only.",
        }
