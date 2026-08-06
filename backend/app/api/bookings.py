"""Tasting bookings CRUD."""

from __future__ import annotations

from typing import Annotated, Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.security import CurrentUser, get_current_user
from app.models.ops_schemas import (
    BookingApproveRequest,
    BookingCreateRequest,
    BookingListResponse,
    BookingOut,
    BookingSummaryRequest,
    BookingUpdateRequest,
)
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])


def get_booking_service() -> BookingService:
    return BookingService()


@router.get("", response_model=BookingListResponse)
async def list_bookings(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    bookings: Annotated[BookingService, Depends(get_booking_service)],
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    rows = await bookings.list(user.id, status_filter=status, search=search)
    return BookingListResponse(bookings=[BookingOut(**r) for r in rows])


@router.post("", response_model=BookingOut)
async def create_booking(
    body: BookingCreateRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    bookings: Annotated[BookingService, Depends(get_booking_service)],
):
    status = "confirmed" if body.approve else "pending"
    row = await bookings.create(
        user.id,
        customer_name=body.customer_name,
        email=str(body.email),
        phone=body.phone,
        booking_date=body.booking_date,
        booking_time=body.booking_time,
        guests=body.guests,
        notes=body.notes,
        title=body.title,
        location=body.location,
        duration_minutes=body.duration_minutes,
        status=status,
        send_confirmation_draft=body.approve,
    )
    return BookingOut(**row)


@router.post("/summary")
async def booking_summary(
    body: BookingSummaryRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    bookings: Annotated[BookingService, Depends(get_booking_service)],
) -> Dict[str, Any]:
    """Return human summary for review before approve (AI flow step)."""
    data = body.model_dump()
    data["email"] = str(body.email)
    data["booking_date"] = body.booking_date.isoformat()
    data["booking_time"] = body.booking_time.strftime("%H:%M")
    return {
        "summary": bookings.summary_text(data),
        "payload": {
            **body.model_dump(mode="json"),
            "email": str(body.email),
        },
    }


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    bookings: Annotated[BookingService, Depends(get_booking_service)],
):
    row = await bookings.get(user.id, booking_id)
    return BookingOut(**row)


@router.put("/{booking_id}", response_model=BookingOut)
async def update_booking(
    booking_id: UUID,
    body: BookingUpdateRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    bookings: Annotated[BookingService, Depends(get_booking_service)],
):
    row = await bookings.update(
        user.id, booking_id, body.model_dump(exclude_unset=True)
    )
    return BookingOut(**row)


@router.post("/{booking_id}/approve", response_model=BookingOut)
async def approve_booking(
    booking_id: UUID,
    body: BookingApproveRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    bookings: Annotated[BookingService, Depends(get_booking_service)],
):
    row = await bookings.approve(user.id, booking_id, confirm=body.confirm)
    return BookingOut(**row)


@router.delete("/{booking_id}", status_code=204)
async def delete_booking(
    booking_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    bookings: Annotated[BookingService, Depends(get_booking_service)],
):
    await bookings.delete(user.id, booking_id)
