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


class StubCalendarService(CalendarService):
    async def create_event(self, event: CalendarEventPayload) -> Dict[str, Any]:
        return {
            "status": "stored_local",
            "provider": "stub",
            "title": event.title,
            "starts_at": event.starts_at,
            "note": "Google Calendar not connected — booking saved in L.U.C.E.R.O.",
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
