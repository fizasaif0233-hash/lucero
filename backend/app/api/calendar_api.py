"""Internal calendar events from PostgreSQL bookings (no Google Calendar)."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.core.security import CurrentUser, get_current_user
from app.models.ops_schemas import CalendarEventOut, CalendarEventsResponse
from app.services.booking_service import BookingService

router = APIRouter(prefix="/calendar", tags=["calendar"])


def get_booking_service() -> BookingService:
    return BookingService()


@router.get("/events", response_model=CalendarEventsResponse)
async def calendar_events(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    bookings: Annotated[BookingService, Depends(get_booking_service)],
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    events = await bookings.calendar_events(user.id, start=start, end=end)
    return CalendarEventsResponse(
        events=[CalendarEventOut(**e) for e in events]
    )
