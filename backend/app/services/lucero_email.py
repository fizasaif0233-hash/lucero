"""Resend-backed outbound email + draft/approval workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.automation.integrations import EmailService, OutboundEmail
from app.core.config import Settings, get_settings
from app.database.client import get_supabase_admin
from app.utils.logging import get_logger

logger = get_logger(__name__)

RESEND_API = "https://api.resend.com/emails"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plain_from_html(html: str) -> str:
    import re

    text = re.sub(r"<br\s*/?>", "\n", html or "", flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


class ResendEmailService(EmailService):
    """Sends via Resend free tier. Falls back to stub-style result if unconfigured."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(self._settings.resend_api_key and self._settings.email_from)

    async def send(self, message: OutboundEmail) -> Dict[str, Any]:
        if not self.configured:
            return {
                "status": "queued_local",
                "provider": "stub",
                "to": message.to,
                "subject": message.subject,
                "note": "RESEND_API_KEY / EMAIL_FROM not set — draft only.",
            }

        html = message.body if "<" in (message.body or "") else None
        text = message.body if html is None else _plain_from_html(message.body)
        payload: Dict[str, Any] = {
            "from": self._settings.email_from,
            "to": [message.to],
            "subject": message.subject,
        }
        if html:
            payload["html"] = message.body
            payload["text"] = text or _plain_from_html(message.body)
        else:
            payload["text"] = message.body or ""

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                RESEND_API,
                headers={
                    "Authorization": f"Bearer {self._settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if res.status_code >= 400:
            detail = res.text
            try:
                detail = res.json()
            except Exception:
                pass
            logger.error("resend_send_failed", status=res.status_code, detail=detail)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Resend error: {detail}",
            )
        data = res.json()
        return {
            "status": "sent",
            "provider": "resend",
            "message_id": data.get("id"),
            "to": message.to,
            "subject": message.subject,
        }


class LuceroEmailService:
    """Draft → preview → approve → send. Never sends without explicit confirm."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._db = get_supabase_admin()
        self._resend = ResendEmailService(self._settings)

    def _log(
        self,
        user_id: str,
        event: str,
        *,
        email_id: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._db.table("email_logs").insert(
            {
                "user_id": user_id,
                "email_id": email_id,
                "event": event,
                "detail": detail or {},
            }
        ).execute()

    def _map(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return row

    async def create_draft(
        self,
        user_id: str | UUID,
        *,
        recipient: str,
        subject: str,
        body_html: str = "",
        body_text: str = "",
        recipient_name: Optional[str] = None,
        template_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        booking_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        uid = str(user_id)
        text = body_text or _plain_from_html(body_html)
        html = body_html or (f"<p>{text}</p>" if text else "")
        row = {
            "user_id": uid,
            "recipient": recipient.strip().lower(),
            "recipient_name": recipient_name,
            "subject": subject.strip(),
            "body_html": html,
            "body_text": text,
            "status": "pending_approval",
            "folder": "drafts",
            "provider": "resend",
            "template_id": str(template_id) if template_id else None,
            "customer_id": str(customer_id) if customer_id else None,
            "booking_id": str(booking_id) if booking_id else None,
        }
        res = self._db.table("emails").insert(row).execute()
        email = (res.data or [None])[0]
        if not email:
            raise HTTPException(500, "Failed to create draft")
        self._log(
            uid,
            "draft_created",
            email_id=email["id"],
            detail={"recipient": recipient, "subject": subject},
        )
        return email

    async def update_draft(
        self, user_id: str | UUID, email_id: str | UUID, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        uid = str(user_id)
        existing = await self.get(uid, email_id)
        if existing["status"] in {"sent", "sending"}:
            raise HTTPException(400, "Cannot edit a sent email")
        payload: Dict[str, Any] = {}
        for key in (
            "recipient",
            "subject",
            "body_html",
            "body_text",
            "recipient_name",
        ):
            if key in updates and updates[key] is not None:
                payload[key] = updates[key]
        if "body_html" in payload and "body_text" not in payload:
            payload["body_text"] = _plain_from_html(payload["body_html"])
        if payload.get("recipient"):
            payload["recipient"] = str(payload["recipient"]).strip().lower()
        payload["status"] = "pending_approval"
        payload["folder"] = "drafts"
        res = (
            self._db.table("emails")
            .update(payload)
            .eq("id", str(email_id))
            .eq("user_id", uid)
            .execute()
        )
        email = (res.data or [None])[0]
        if not email:
            raise HTTPException(404, "Email not found")
        self._log(uid, "draft_edited", email_id=str(email_id), detail=payload)
        return email

    async def approve(self, user_id: str | UUID, email_id: str | UUID) -> Dict[str, Any]:
        uid = str(user_id)
        existing = await self.get(uid, email_id)
        if existing["status"] in {"sent", "cancelled"}:
            raise HTTPException(400, f"Cannot approve email in status {existing['status']}")
        res = (
            self._db.table("emails")
            .update(
                {
                    "status": "approved",
                    "approved_at": _now_iso(),
                    "folder": "drafts",
                }
            )
            .eq("id", str(email_id))
            .eq("user_id", uid)
            .execute()
        )
        email = (res.data or [None])[0]
        self._log(uid, "approved", email_id=str(email_id))
        return email

    async def cancel(self, user_id: str | UUID, email_id: str | UUID) -> Dict[str, Any]:
        uid = str(user_id)
        existing = await self.get(uid, email_id)
        if existing["status"] == "sent":
            raise HTTPException(400, "Cannot cancel a sent email")
        res = (
            self._db.table("emails")
            .update({"status": "cancelled", "folder": "drafts"})
            .eq("id", str(email_id))
            .eq("user_id", uid)
            .execute()
        )
        email = (res.data or [None])[0]
        self._log(uid, "cancelled", email_id=str(email_id))
        return email

    async def send_approved(
        self, user_id: str | UUID, email_id: str | UUID, *, confirm: bool
    ) -> Dict[str, Any]:
        if not confirm:
            raise HTTPException(
                400,
                "confirm=true is required. Emails never send automatically.",
            )
        uid = str(user_id)
        email = await self.get(uid, email_id)
        if email["status"] == "sent":
            raise HTTPException(400, "Email already sent")
        if email["status"] == "cancelled":
            raise HTTPException(400, "Email was cancelled")
        if email["status"] not in {"approved", "failed", "pending_approval"}:
            raise HTTPException(
                400,
                "Approve the email on the review page before sending "
                "(or retry a failed send).",
            )
        # Require explicit prior approve for first send; failed can retry
        if email["status"] == "pending_approval":
            raise HTTPException(
                400,
                "Preview and Approve the draft before sending.",
            )

        self._db.table("emails").update({"status": "sending"}).eq(
            "id", str(email_id)
        ).eq("user_id", uid).execute()
        self._log(uid, "send_attempt", email_id=str(email_id))

        body = email.get("body_html") or email.get("body_text") or ""
        try:
            result = await self._resend.send(
                OutboundEmail(
                    to=email["recipient"],
                    subject=email["subject"],
                    body=body,
                    to_name=email.get("recipient_name"),
                )
            )
        except HTTPException as exc:
            self._db.table("emails").update(
                {
                    "status": "failed",
                    "folder": "failed",
                    "error_message": str(exc.detail),
                }
            ).eq("id", str(email_id)).eq("user_id", uid).execute()
            self._log(
                uid,
                "send_failed",
                email_id=str(email_id),
                detail={"error": str(exc.detail)},
            )
            raise

        provider = result.get("provider") or "resend"
        message_id = result.get("message_id")
        if result.get("status") == "queued_local":
            # No Resend credentials — keep as approved with note
            updated = (
                self._db.table("emails")
                .update(
                    {
                        "status": "failed",
                        "folder": "failed",
                        "error_message": result.get("note")
                        or "Resend not configured",
                        "provider": provider,
                    }
                )
                .eq("id", str(email_id))
                .eq("user_id", uid)
                .execute()
            )
            self._log(uid, "send_failed", email_id=str(email_id), detail=result)
            return (updated.data or [email])[0]

        updated = (
            self._db.table("emails")
            .update(
                {
                    "status": "sent",
                    "folder": "sent",
                    "provider": provider,
                    "message_id": message_id,
                    "sent_at": _now_iso(),
                    "error_message": None,
                }
            )
            .eq("id", str(email_id))
            .eq("user_id", uid)
            .execute()
        )
        sent_row = (updated.data or [None])[0] or email
        self._log(uid, "sent", email_id=str(email_id), detail=result)

        # CRM email history
        self._db.table("crm_email_history").insert(
            {
                "user_id": uid,
                "customer_id": email.get("customer_id"),
                "email_id": str(email_id),
                "recipient": email["recipient"],
                "subject": email["subject"],
                "status": "sent",
                "sent_at": _now_iso(),
            }
        ).execute()
        if email.get("customer_id"):
            self._db.table("crm_activities").insert(
                {
                    "user_id": uid,
                    "customer_id": email["customer_id"],
                    "email_id": str(email_id),
                    "booking_id": email.get("booking_id"),
                    "activity_type": "email_sent",
                    "title": f"Email sent: {email['subject']}",
                    "body": email.get("body_text") or "",
                    "metadata": {"message_id": message_id},
                }
            ).execute()
        return sent_row

    async def retry(self, user_id: str | UUID, email_id: str | UUID) -> Dict[str, Any]:
        uid = str(user_id)
        email = await self.get(uid, email_id)
        if email["status"] != "failed":
            raise HTTPException(400, "Only failed emails can be retried")
        self._db.table("emails").update({"status": "approved"}).eq(
            "id", str(email_id)
        ).eq("user_id", uid).execute()
        return await self.send_approved(uid, email_id, confirm=True)

    async def get(self, user_id: str | UUID, email_id: str | UUID) -> Dict[str, Any]:
        res = (
            self._db.table("emails")
            .select("*")
            .eq("id", str(email_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        if not res.data:
            raise HTTPException(404, "Email not found")
        return res.data[0]

    async def list_emails(
        self,
        user_id: str | UUID,
        *,
        folder: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        q = (
            self._db.table("emails")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
        )
        if folder:
            q = q.eq("folder", folder)
        if status_filter:
            q = q.eq("status", status_filter)
        return list(q.execute().data or [])

    async def list_logs(
        self, user_id: str | UUID, *, limit: int = 100
    ) -> List[Dict[str, Any]]:
        res = (
            self._db.table("email_logs")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(res.data or [])

    async def create_template(
        self, user_id: str | UUID, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        row = {
            "user_id": str(user_id),
            "name": data["name"],
            "subject": data["subject"],
            "body_html": data.get("body_html") or "",
            "body_text": data.get("body_text")
            or _plain_from_html(data.get("body_html") or ""),
            "category": data.get("category") or "general",
        }
        res = self._db.table("email_templates").insert(row).execute()
        return (res.data or [None])[0]

    async def list_templates(self, user_id: str | UUID) -> List[Dict[str, Any]]:
        res = (
            self._db.table("email_templates")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        return list(res.data or [])

    async def ensure_default_templates(self, user_id: str | UUID) -> None:
        existing = await self.list_templates(user_id)
        if existing:
            return
        defaults = [
            {
                "name": "Tasting confirmation",
                "subject": "Your tasting is confirmed",
                "body_html": (
                    "<p>Hi {{name}},</p>"
                    "<p>Your tasting on <strong>{{date}}</strong> at "
                    "<strong>{{time}}</strong> for {{guests}} guests is confirmed.</p>"
                    "<p>We look forward to hosting you.</p>"
                ),
                "category": "booking",
            },
            {
                "name": "Tasting reminder",
                "subject": "Reminder: tasting coming up",
                "body_html": (
                    "<p>Hi {{name}},</p>"
                    "<p>This is a friendly reminder of your tasting on "
                    "<strong>{{date}}</strong> at <strong>{{time}}</strong>.</p>"
                ),
                "category": "reminder",
            },
        ]
        for t in defaults:
            await self.create_template(user_id, t)
