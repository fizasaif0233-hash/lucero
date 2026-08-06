"""Tasting bookings + internal PostgreSQL calendar events."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.database.client import get_supabase_admin
from app.services.crm_service import CrmService
from app.services.lucero_email import LuceroEmailService
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def booking_to_out(row: Dict[str, Any]) -> Dict[str, Any]:
    starts = _parse_dt(row.get("starts_at"))
    ends = _parse_dt(row.get("ends_at"))
    booking_date = starts.date().isoformat() if starts else None
    booking_time = starts.strftime("%H:%M") if starts else None
    guests = row.get("guest_count")
    if guests is None:
        g = row.get("guests")
        guests = len(g) if isinstance(g, list) else (int(g) if g else 1)
    return {
        "id": row["id"],
        "title": row.get("title") or "Tasting",
        "customer_name": row.get("customer_name"),
        "email": row.get("customer_email"),
        "phone": row.get("phone"),
        "booking_date": booking_date,
        "booking_time": booking_time,
        "guests": int(guests or 1),
        "notes": row.get("notes") or row.get("description"),
        "status": row.get("status") or "pending",
        "location": row.get("location"),
        "description": row.get("description"),
        "starts_at": row.get("starts_at"),
        "ends_at": row.get("ends_at"),
        "customer_id": row.get("customer_id"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


class BookingService:
    def __init__(self) -> None:
        self._db = get_supabase_admin()
        self._crm = CrmService()
        self._email = LuceroEmailService()

    def _combine(self, d: date, t: time) -> datetime:
        return datetime.combine(d, t).replace(tzinfo=timezone.utc)

    def _assert_no_duplicate(
        self,
        user_id: str,
        starts_at: datetime,
        email: str,
        *,
        exclude_id: Optional[str] = None,
    ) -> None:
        """Prevent same customer + same start window."""
        q = (
            self._db.table("bookings")
            .select("id, status")
            .eq("user_id", user_id)
            .eq("customer_email", email.strip().lower())
            .eq("starts_at", starts_at.isoformat())
            .neq("status", "cancelled")
        )
        rows = list(q.execute().data or [])
        if exclude_id:
            rows = [r for r in rows if r["id"] != exclude_id]
        if rows:
            raise HTTPException(
                409,
                "A booking already exists for this customer at that date/time.",
            )

    async def create(
        self,
        user_id: str | UUID,
        *,
        customer_name: str,
        email: str,
        phone: Optional[str],
        booking_date: date,
        booking_time: time,
        guests: int,
        notes: Optional[str] = None,
        title: Optional[str] = None,
        location: Optional[str] = None,
        duration_minutes: int = 120,
        status: str = "pending",
        run_id: Optional[str] = None,
        send_confirmation_draft: bool = True,
        schedule_reminders: bool = True,
    ) -> Dict[str, Any]:
        uid = str(user_id)
        email_norm = email.strip().lower()
        starts = self._combine(booking_date, booking_time)
        ends = starts + timedelta(minutes=duration_minutes)
        self._assert_no_duplicate(uid, starts, email_norm)

        customer = self._crm.upsert_customer(
            uid,
            name=customer_name,
            email=email_norm,
            phone=phone,
            notes=notes,
        )

        event_title = title or f"Tasting — {customer_name}"
        row = {
            "user_id": uid,
            "run_id": run_id,
            "title": event_title,
            "description": notes,
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat(),
            "location": location,
            "guests": [email_norm],
            "guest_count": guests,
            "status": status,
            "customer_id": customer["id"],
            "customer_name": customer_name,
            "customer_email": email_norm,
            "phone": phone,
            "notes": notes,
            "external_calendar_id": f"lucero:{uid}",
        }
        res = self._db.table("bookings").insert(row).execute()
        booking = (res.data or [None])[0]
        if not booking:
            raise HTTPException(500, "Failed to create booking")

        self._crm.add_activity(
            uid,
            customer_id=customer["id"],
            booking_id=booking["id"],
            activity_type="booking_created",
            title=f"Booking {status}: {event_title}",
            body=notes,
            metadata={"guests": guests, "starts_at": starts.isoformat()},
        )

        if schedule_reminders and status in {"pending", "confirmed"}:
            await self._schedule_reminders(uid, booking)

        if send_confirmation_draft and status == "confirmed":
            await self._create_confirmation_draft(uid, booking)

        return booking_to_out(booking)

    async def _schedule_reminders(
        self, user_id: str, booking: Dict[str, Any]
    ) -> None:
        starts = _parse_dt(booking.get("starts_at"))
        if not starts:
            return
        from app.services.reminder_service import ReminderService

        await ReminderService().schedule_for_booking(user_id, booking["id"], starts)

    async def _create_confirmation_draft(
        self, user_id: str, booking: Dict[str, Any]
    ) -> None:
        name = booking.get("customer_name") or "Guest"
        starts = _parse_dt(booking.get("starts_at"))
        date_s = starts.strftime("%Y-%m-%d") if starts else ""
        time_s = starts.strftime("%H:%M") if starts else ""
        guests = booking.get("guest_count") or 1
        await self._email.create_draft(
            user_id,
            recipient=booking.get("customer_email") or "",
            recipient_name=name,
            subject="Your tasting is confirmed",
            body_html=(
                f"<p>Hi {name},</p>"
                f"<p>Your tasting on <strong>{date_s}</strong> at "
                f"<strong>{time_s}</strong> for {guests} guests is confirmed.</p>"
                f"<p>We look forward to hosting you.</p>"
            ),
            customer_id=booking.get("customer_id"),
            booking_id=booking.get("id"),
        )

    async def list(
        self,
        user_id: str | UUID,
        *,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        q = (
            self._db.table("bookings")
            .select("*")
            .eq("user_id", str(user_id))
            .order("starts_at", desc=False)
        )
        if status_filter:
            q = q.eq("status", status_filter)
        if from_dt:
            q = q.gte("starts_at", from_dt.isoformat())
        if to_dt:
            q = q.lte("starts_at", to_dt.isoformat())
        rows = list(q.execute().data or [])
        if search:
            s = search.lower()
            rows = [
                r
                for r in rows
                if s in (r.get("customer_name") or "").lower()
                or s in (r.get("customer_email") or "").lower()
                or s in (r.get("title") or "").lower()
                or s in (r.get("phone") or "")
            ]
        return [booking_to_out(r) for r in rows]

    async def get(self, user_id: str | UUID, booking_id: str | UUID) -> Dict[str, Any]:
        res = (
            self._db.table("bookings")
            .select("*")
            .eq("id", str(booking_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        if not res.data:
            raise HTTPException(404, "Booking not found")
        return booking_to_out(res.data[0])

    async def update(
        self,
        user_id: str | UUID,
        booking_id: str | UUID,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        uid = str(user_id)
        existing_res = (
            self._db.table("bookings")
            .select("*")
            .eq("id", str(booking_id))
            .eq("user_id", uid)
            .limit(1)
            .execute()
        )
        if not existing_res.data:
            raise HTTPException(404, "Booking not found")
        existing = existing_res.data[0]

        payload: Dict[str, Any] = {}
        if "customer_name" in updates and updates["customer_name"] is not None:
            payload["customer_name"] = updates["customer_name"]
            payload["title"] = updates.get("title") or f"Tasting — {updates['customer_name']}"
        if "email" in updates and updates["email"] is not None:
            payload["customer_email"] = str(updates["email"]).strip().lower()
            payload["guests"] = [payload["customer_email"]]
        if "phone" in updates and updates["phone"] is not None:
            payload["phone"] = updates["phone"]
        if "notes" in updates and updates["notes"] is not None:
            payload["notes"] = updates["notes"]
            payload["description"] = updates["notes"]
        if "guests" in updates and updates["guests"] is not None:
            payload["guest_count"] = updates["guests"]
        if "location" in updates and updates["location"] is not None:
            payload["location"] = updates["location"]
        if "title" in updates and updates["title"] is not None:
            payload["title"] = updates["title"]
        if "status" in updates and updates["status"] is not None:
            st = updates["status"].lower()
            if st not in {"pending", "confirmed", "completed", "cancelled", "draft"}:
                raise HTTPException(400, f"Invalid status: {st}")
            payload["status"] = st

        d = updates.get("booking_date")
        t = updates.get("booking_time")
        if d is not None or t is not None:
            starts_old = _parse_dt(existing.get("starts_at")) or datetime.now(timezone.utc)
            new_d = d if d is not None else starts_old.date()
            new_t = t if t is not None else starts_old.timetz().replace(tzinfo=None)
            duration = updates.get("duration_minutes") or 120
            starts = self._combine(new_d, new_t)
            ends = starts + timedelta(minutes=duration)
            email_for_dup = payload.get("customer_email") or existing.get(
                "customer_email"
            )
            if email_for_dup:
                self._assert_no_duplicate(
                    uid, starts, email_for_dup, exclude_id=str(booking_id)
                )
            payload["starts_at"] = starts.isoformat()
            payload["ends_at"] = ends.isoformat()

            # Reschedule reminders
            from app.services.reminder_service import ReminderService

            await ReminderService().cancel_for_booking(uid, str(booking_id))
            if payload.get("status", existing.get("status")) != "cancelled":
                await ReminderService().schedule_for_booking(
                    uid, str(booking_id), starts
                )

        if not payload:
            return booking_to_out(existing)

        res = (
            self._db.table("bookings")
            .update(payload)
            .eq("id", str(booking_id))
            .eq("user_id", uid)
            .execute()
        )
        booking = (res.data or [None])[0] or existing
        if booking.get("customer_id"):
            self._crm.add_activity(
                uid,
                customer_id=booking["customer_id"],
                booking_id=str(booking_id),
                activity_type="booking_updated",
                title="Booking updated",
                metadata=payload,
            )
        # Confirmation draft when newly confirmed
        if (
            payload.get("status") == "confirmed"
            and existing.get("status") != "confirmed"
        ):
            await self._create_confirmation_draft(uid, booking)
        return booking_to_out(booking)

    async def delete(self, user_id: str | UUID, booking_id: str | UUID) -> None:
        """Soft-cancel (preserve history)."""
        await self.update(user_id, booking_id, {"status": "cancelled"})
        from app.services.reminder_service import ReminderService

        await ReminderService().cancel_for_booking(str(user_id), str(booking_id))

    async def approve(
        self, user_id: str | UUID, booking_id: str | UUID, *, confirm: bool
    ) -> Dict[str, Any]:
        if not confirm:
            raise HTTPException(400, "confirm=true required")
        return await self.update(user_id, booking_id, {"status": "confirmed"})

    async def calendar_events(
        self,
        user_id: str | UUID,
        *,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q = (
            self._db.table("bookings")
            .select("*")
            .eq("user_id", str(user_id))
            .neq("status", "draft")
        )
        if start:
            q = q.gte("starts_at", start)
        if end:
            q = q.lte("starts_at", end)
        rows = list(q.execute().data or [])
        events = []
        for r in rows:
            out = booking_to_out(r)
            events.append(
                {
                    "id": str(r["id"]),
                    "title": out["title"],
                    "start": r.get("starts_at"),
                    "end": r.get("ends_at"),
                    "status": out["status"],
                    "extendedProps": {
                        "customer_name": out.get("customer_name"),
                        "email": out.get("email"),
                        "phone": out.get("phone"),
                        "guests": out.get("guests"),
                        "notes": out.get("notes"),
                        "status": out["status"],
                    },
                }
            )
        return events

    def summary_text(self, data: Dict[str, Any]) -> str:
        return (
            f"Tasting for {data['customer_name']} ({data['email']})\n"
            f"Phone: {data.get('phone') or '—'}\n"
            f"When: {data['booking_date']} at {data['booking_time']}\n"
            f"Guests: {data['guests']}\n"
            f"Notes: {data.get('notes') or '—'}\n\n"
            "Approve to save this booking and prepare a confirmation email draft."
        )
