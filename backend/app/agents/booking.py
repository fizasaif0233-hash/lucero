"""Booking Automation Agent — create / cancel / reschedule / status (new agent only)."""

from __future__ import annotations

import re
from typing import List
from uuid import UUID

from app.agents.specialist_base import AgentContext, AgentInfo, SpecialistAgent
from app.services.booking_service import BookingService


class BookingAgent(SpecialistAgent):
    """
    New specialist for tasting bookings.
    Does not modify SupportAgent — complements it with live booking data.
    """

    info = AgentInfo(
        id="booking",
        name="Booking Automation",
        title="Booking & Calendar",
        description=(
            "Create, cancel, reschedule tastings; confirm availability; "
            "draft confirmation and reminder emails for review."
        ),
        skills=(
            "Create booking",
            "Cancel booking",
            "Reschedule booking",
            "Booking status",
            "Availability",
            "Confirmation email draft",
            "Reminder email draft",
        ),
        icon="calendar",
        status="ready",
    )

    _PATTERNS = (
        r"\bbook(ing|ed)?\b",
        r"\btasting\b",
        r"\breschedul",
        r"\bcancel(l?ation|led)?\b",
        r"\bavailability\b",
        r"\bcalendar\b",
        r"\bappointment\b",
        r"\bguests?\b",
        r"\bconfirm(ation)?\b",
        r"\breminder\b",
    )

    def relevance(self, message: str) -> float:
        lower = message.lower()
        hits = sum(1 for p in self._PATTERNS if re.search(p, lower))
        if re.search(r"\bbook a tasting\b", lower):
            return 0.95
        return min(0.95, 0.45 + 0.12 * hits) if hits else 0.05

    def knowledge_queries(self, message: str) -> List[str]:
        return [
            message,
            "tasting booking hours availability policy",
            "759 Tequila tasting experience guests",
        ]

    def role_instructions(self) -> str:
        return (
            "You are L.U.C.E.R.O Booking Automation Agent. "
            "Help create, cancel, or reschedule tastings. "
            "Collect: name, email, phone, date, time, guests, notes. "
            "Always present a clear summary and tell the user to Approve "
            "in /dashboard/bookings (never invent a confirmed booking). "
            "For status questions, use the live booking list in context. "
            "Confirmation and reminder emails go through Email review — never auto-send. "
            "Do not invent availability that conflicts with listed bookings."
        )

    async def gather_context(
        self, *, user_id: str | UUID, message: str
    ) -> AgentContext:
        base = await super().gather_context(user_id=user_id, message=message)
        try:
            bookings = await BookingService().list(user_id)
            upcoming = [
                b
                for b in bookings
                if b.get("status") in {"pending", "confirmed"}
            ][:15]
            lines = []
            for b in upcoming:
                lines.append(
                    f"- {b.get('booking_date')} {b.get('booking_time')} | "
                    f"{b.get('customer_name')} <{b.get('email')}> | "
                    f"{b.get('guests')} guests | {b.get('status')} | id={b.get('id')}"
                )
            block = (
                "## Live bookings (internal calendar)\n"
                + ("\n".join(lines) if lines else "No upcoming bookings.")
            )
            base.knowledge = f"{base.knowledge}\n\n{block}".strip()
            base.metadata["booking_count"] = len(upcoming)
        except Exception:
            pass
        return base
