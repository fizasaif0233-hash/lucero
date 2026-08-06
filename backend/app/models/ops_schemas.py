"""Pydantic schemas for email, bookings, calendar, CRM, reminders."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ---- Email ----


class EmailDraftRequest(BaseModel):
    recipient: EmailStr
    subject: str = Field(..., min_length=1, max_length=500)
    body_html: str = ""
    body_text: str = ""
    recipient_name: Optional[str] = None
    template_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None


class EmailUpdateRequest(BaseModel):
    recipient: Optional[EmailStr] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    recipient_name: Optional[str] = None


class EmailSendRequest(BaseModel):
    """Send only after explicit confirmation. Never auto-send."""

    email_id: UUID
    confirm: bool = Field(
        ...,
        description="Must be true. Emails never send without explicit confirm.",
    )


class EmailTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    subject: str = Field(..., min_length=1, max_length=500)
    body_html: str = ""
    body_text: str = ""
    category: str = "general"


class EmailOut(BaseModel):
    id: UUID
    recipient: str
    recipient_name: Optional[str] = None
    subject: str
    body_html: str = ""
    body_text: str = ""
    status: str
    provider: str = "resend"
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    folder: str = "drafts"
    customer_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None
    template_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None


class EmailListResponse(BaseModel):
    emails: List[EmailOut]


class EmailTemplateOut(BaseModel):
    id: UUID
    name: str
    subject: str
    body_html: str = ""
    body_text: str = ""
    category: str = "general"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EmailTemplateListResponse(BaseModel):
    templates: List[EmailTemplateOut]


class EmailLogOut(BaseModel):
    id: UUID
    email_id: Optional[UUID] = None
    event: str
    detail: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class EmailLogListResponse(BaseModel):
    logs: List[EmailLogOut]


# ---- Bookings ----


class BookingCreateRequest(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=40)
    booking_date: date
    booking_time: time
    guests: int = Field(1, ge=1, le=100)
    notes: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    duration_minutes: int = Field(120, ge=30, le=480)
    approve: bool = Field(
        False,
        description="If false, creates pending draft. If true, confirms booking.",
    )


class BookingUpdateRequest(BaseModel):
    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    booking_date: Optional[date] = None
    booking_time: Optional[time] = None
    guests: Optional[int] = Field(None, ge=1, le=100)
    notes: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=30, le=480)


class BookingOut(BaseModel):
    id: UUID
    title: str
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    booking_date: Optional[str] = None
    booking_time: Optional[str] = None
    guests: int = 1
    notes: Optional[str] = None
    status: str
    location: Optional[str] = None
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    customer_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BookingListResponse(BaseModel):
    bookings: List[BookingOut]


class BookingSummaryRequest(BaseModel):
    """AI-assisted tasting booking: collect → summary → approve."""

    customer_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: Optional[str] = None
    booking_date: date
    booking_time: time
    guests: int = Field(1, ge=1, le=100)
    notes: Optional[str] = None


class BookingApproveRequest(BaseModel):
    confirm: bool = True


# ---- Calendar ----


class CalendarEventOut(BaseModel):
    id: str
    title: str
    start: str
    end: Optional[str] = None
    status: str
    extendedProps: Dict[str, Any] = Field(default_factory=dict)


class CalendarEventsResponse(BaseModel):
    events: List[CalendarEventOut]


# ---- CRM ----


class CustomerOut(BaseModel):
    id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CustomerListResponse(BaseModel):
    customers: List[CustomerOut]


class CrmActivityOut(BaseModel):
    id: UUID
    customer_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None
    email_id: Optional[UUID] = None
    activity_type: str
    title: str
    body: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class CustomerProfileOut(BaseModel):
    customer: CustomerOut
    bookings: List[BookingOut] = []
    email_history: List[Dict[str, Any]] = []
    timeline: List[CrmActivityOut] = []


# ---- Reminders ----


class ReminderOut(BaseModel):
    id: UUID
    booking_id: UUID
    type: str
    scheduled_time: datetime
    status: str
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class ReminderListResponse(BaseModel):
    reminders: List[ReminderOut]


class ReminderRunResponse(BaseModel):
    processed: int
    sent: int
    failed: int
    details: List[Dict[str, Any]] = Field(default_factory=list)
