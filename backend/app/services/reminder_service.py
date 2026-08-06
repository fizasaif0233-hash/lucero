"""Booking reminder scheduler — 24h and 1h emails via Resend."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.database.client import get_supabase_admin
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


class ReminderService:
    def __init__(self) -> None:
        self._db = get_supabase_admin()
        self._email = LuceroEmailService()

    async def schedule_for_booking(
        self,
        user_id: str | UUID,
        booking_id: str,
        starts_at: datetime,
    ) -> List[Dict[str, Any]]:
        uid = str(user_id)
        now = datetime.now(timezone.utc)
        created: List[Dict[str, Any]] = []
        plans = [
            ("24h", starts_at - timedelta(hours=24)),
            ("1h", starts_at - timedelta(hours=1)),
        ]
        for rtype, when in plans:
            if when <= now:
                continue
            existing = (
                self._db.table("reminders")
                .select("id")
                .eq("booking_id", booking_id)
                .eq("type", rtype)
                .eq("status", "pending")
                .limit(1)
                .execute()
            )
            if existing.data:
                continue
            res = (
                self._db.table("reminders")
                .insert(
                    {
                        "user_id": uid,
                        "booking_id": booking_id,
                        "type": rtype,
                        "scheduled_time": when.isoformat(),
                        "status": "pending",
                    }
                )
                .execute()
            )
            if res.data:
                created.append(res.data[0])
        return created

    async def cancel_for_booking(self, user_id: str | UUID, booking_id: str) -> None:
        self._db.table("reminders").update({"status": "cancelled"}).eq(
            "booking_id", booking_id
        ).eq("user_id", str(user_id)).eq("status", "pending").execute()

    async def list_for_user(self, user_id: str | UUID) -> List[Dict[str, Any]]:
        res = (
            self._db.table("reminders")
            .select("*")
            .eq("user_id", str(user_id))
            .order("scheduled_time", desc=False)
            .limit(200)
            .execute()
        )
        return list(res.data or [])

    async def run_due(self, *, limit: int = 50) -> Dict[str, Any]:
        """Process pending reminders whose scheduled_time has passed."""
        now = datetime.now(timezone.utc).isoformat()
        due = (
            self._db.table("reminders")
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_time", now)
            .limit(limit)
            .execute()
        )
        rows = list(due.data or [])
        sent = 0
        failed = 0
        details: List[Dict[str, Any]] = []

        for rem in rows:
            try:
                result = await self._send_one(rem)
                details.append(result)
                if result.get("ok"):
                    sent += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self._db.table("reminders").update(
                    {"status": "failed", "error_message": str(exc)}
                ).eq("id", rem["id"]).execute()
                details.append({"id": rem["id"], "ok": False, "error": str(exc)})
                logger.exception("reminder_failed", reminder_id=rem["id"])

        return {
            "processed": len(rows),
            "sent": sent,
            "failed": failed,
            "details": details,
        }

    async def _send_one(self, rem: Dict[str, Any]) -> Dict[str, Any]:
        booking_res = (
            self._db.table("bookings")
            .select("*")
            .eq("id", rem["booking_id"])
            .limit(1)
            .execute()
        )
        if not booking_res.data:
            self._db.table("reminders").update(
                {"status": "cancelled", "error_message": "booking missing"}
            ).eq("id", rem["id"]).execute()
            return {"id": rem["id"], "ok": False, "error": "booking missing"}

        booking = booking_res.data[0]
        if booking.get("status") in {"cancelled", "completed"}:
            self._db.table("reminders").update({"status": "cancelled"}).eq(
                "id", rem["id"]
            ).execute()
            return {"id": rem["id"], "ok": False, "error": "booking not active"}

        recipient = booking.get("customer_email")
        if not recipient:
            self._db.table("reminders").update(
                {"status": "failed", "error_message": "no customer email"}
            ).eq("id", rem["id"]).execute()
            return {"id": rem["id"], "ok": False, "error": "no email"}

        name = booking.get("customer_name") or "Guest"
        starts = _parse_dt(booking.get("starts_at"))
        date_s = starts.strftime("%Y-%m-%d") if starts else ""
        time_s = starts.strftime("%H:%M") if starts else ""
        label = "24 hours" if rem["type"] == "24h" else "1 hour"

        draft = await self._email.create_draft(
            rem["user_id"],
            recipient=recipient,
            recipient_name=name,
            subject=f"Reminder: tasting in {label}",
            body_html=(
                f"<p>Hi {name},</p>"
                f"<p>This is a reminder that your tasting is in {label} "
                f"(<strong>{date_s}</strong> at <strong>{time_s}</strong>).</p>"
            ),
            customer_id=booking.get("customer_id"),
            booking_id=booking.get("id"),
        )
        await self._email.approve(rem["user_id"], draft["id"])
        sent = await self._email.send_approved(
            rem["user_id"], draft["id"], confirm=True
        )

        ok = sent.get("status") == "sent"
        self._db.table("reminders").update(
            {
                "status": "sent" if ok else "failed",
                "email_id": draft["id"],
                "sent_at": datetime.now(timezone.utc).isoformat() if ok else None,
                "error_message": None if ok else sent.get("error_message"),
            }
        ).eq("id", rem["id"]).execute()
        return {"id": rem["id"], "ok": ok, "email_id": draft["id"]}
