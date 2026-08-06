"""CRM customers, timeline, and email history helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.database.client import get_supabase_admin


class CrmService:
    def __init__(self) -> None:
        self._db = get_supabase_admin()

    def upsert_customer(
        self,
        user_id: str | UUID,
        *,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        uid = str(user_id)
        email_norm = (email or "").strip().lower() or None

        if email_norm:
            found = (
                self._db.table("customers")
                .select("*")
                .eq("user_id", uid)
                .ilike("email", email_norm)
                .limit(1)
                .execute()
            )
            if found.data:
                row = found.data[0]
                updates: Dict[str, Any] = {"name": name}
                if phone:
                    updates["phone"] = phone
                if notes:
                    updates["notes"] = (
                        (row.get("notes") or "") + ("\n" + notes if row.get("notes") else notes)
                    ).strip()
                res = (
                    self._db.table("customers")
                    .update(updates)
                    .eq("id", row["id"])
                    .execute()
                )
                return (res.data or [row])[0]

        res = (
            self._db.table("customers")
            .insert(
                {
                    "user_id": uid,
                    "name": name.strip(),
                    "email": email_norm,
                    "phone": phone,
                    "notes": notes,
                }
            )
            .execute()
        )
        return (res.data or [None])[0]

    def add_activity(
        self,
        user_id: str | UUID,
        *,
        customer_id: str,
        activity_type: str,
        title: str,
        body: Optional[str] = None,
        booking_id: Optional[str] = None,
        email_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        res = (
            self._db.table("crm_activities")
            .insert(
                {
                    "user_id": str(user_id),
                    "customer_id": customer_id,
                    "booking_id": booking_id,
                    "email_id": email_id,
                    "activity_type": activity_type,
                    "title": title,
                    "body": body,
                    "metadata": metadata or {},
                }
            )
            .execute()
        )
        return (res.data or [None])[0]

    def list_customers(self, user_id: str | UUID) -> List[Dict[str, Any]]:
        res = (
            self._db.table("customers")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        return list(res.data or [])

    def get_profile(self, user_id: str | UUID, customer_id: str) -> Dict[str, Any]:
        uid = str(user_id)
        cust = (
            self._db.table("customers")
            .select("*")
            .eq("id", customer_id)
            .eq("user_id", uid)
            .limit(1)
            .execute()
        )
        if not cust.data:
            raise HTTPException(404, "Customer not found")
        customer = cust.data[0]
        bookings = (
            self._db.table("bookings")
            .select("*")
            .eq("user_id", uid)
            .eq("customer_id", customer_id)
            .order("starts_at", desc=True)
            .execute()
        )
        emails = (
            self._db.table("crm_email_history")
            .select("*")
            .eq("user_id", uid)
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .execute()
        )
        timeline = (
            self._db.table("crm_activities")
            .select("*")
            .eq("user_id", uid)
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        return {
            "customer": customer,
            "bookings": list(bookings.data or []),
            "email_history": list(emails.data or []),
            "timeline": list(timeline.data or []),
        }
