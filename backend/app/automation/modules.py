"""Automation module implementations."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.ai.service import AIService
from app.automation.base import (
    AutomationModule,
    AutomationModuleBase,
    DraftBundle,
    DraftItem,
    ExecuteResult,
)
from app.automation.crm_data import contacts_as_text, load_crm_contacts
from app.automation.integrations import (
    CalendarEventPayload,
    CalendarService,
    EmailService,
    MessagingService,
    OutboundEmail,
    StubCalendarService,
    StubEmailService,
    StubMessagingService,
)
from app.database.client import get_supabase_admin
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match:
            return json.loads(match.group(1))
        raise


class EmailAutomation(AutomationModuleBase):
    module = AutomationModule.EMAIL
    label = "Email Automation"
    description = "Draft personalized emails from CRM/distributor contacts for review before send."

    def __init__(
        self,
        ai: AIService,
        email_service: Optional[EmailService] = None,
    ) -> None:
        self._ai = ai
        self._email = email_service or StubEmailService()

    async def plan_and_draft(
        self, *, user_id: str | UUID, prompt: str, knowledge: str = ""
    ) -> DraftBundle:
        contacts = load_crm_contacts()
        # Prefer contacts with emails; still draft for HOT without email using placeholder
        selected = [
            c
            for c in contacts
            if (c.get("priority") or "").upper() in {"HOT", "HIGH"}
            or "distributor" in (c.get("type") or "").lower()
        ][:12]
        if not selected:
            selected = contacts[:8]

        contact_block = contacts_as_text(selected)
        system = (
            "You are L.U.C.E.R.O preparing outbound business emails. "
            "Return ONLY valid JSON: "
            '{"plan":"...", "emails":[{"to":"","to_name":"","company":"","subject":"","body":""}]} '
            "Use real emails when present. If missing, set to to 'MISSING_EMAIL' and still draft. "
            "Personalize using Intel/Angle. Do not invent fake email addresses."
        )
        raw = await self._ai.complete_task(
            system,
            f"User request: {prompt}\n\nCRM contacts:\n{contact_block}\n\n"
            f"Extra knowledge:\n{knowledge[:4000]}",
            temperature=0.35,
        )
        data = _extract_json(raw)
        emails = data.get("emails") if isinstance(data, dict) else data
        items: List[DraftItem] = []
        for i, em in enumerate(emails or []):
            items.append(
                DraftItem(
                    item_type="email",
                    title=f"{em.get('company') or em.get('to_name') or 'Recipient'}: {em.get('subject') or 'Email'}",
                    content={
                        "to": em.get("to") or "MISSING_EMAIL",
                        "to_name": em.get("to_name") or "",
                        "company": em.get("company") or "",
                        "subject": em.get("subject") or "",
                        "body": em.get("body") or "",
                    },
                    sort_order=i,
                )
            )
        return DraftBundle(
            title="Distributor outreach emails",
            plan_summary=data.get("plan")
            if isinstance(data, dict)
            else f"Prepared {len(items)} personalized emails for review.",
            items=items,
            preview={
                "confirmation_prompt": "Review complete. Would you like to send these emails?",
                "count": len(items),
            },
        )

    async def execute(
        self,
        *,
        user_id: str | UUID,
        run_id: str | UUID,
        items: List[dict],
        preview: Dict[str, Any],
    ) -> ExecuteResult:
        sent = []
        skipped = []
        for item in items:
            content = item.get("content") or {}
            to = (content.get("to") or "").strip()
            if not to or to == "MISSING_EMAIL":
                skipped.append(content.get("company") or item.get("title"))
                continue
            result = await self._email.send(
                OutboundEmail(
                    to=to,
                    subject=content.get("subject") or "(no subject)",
                    body=content.get("body") or "",
                    to_name=content.get("to_name"),
                )
            )
            sent.append({"to": to, "result": result})
        return ExecuteResult(
            summary=(
                f"Processed {len(items)} emails: {len(sent)} queued, "
                f"{len(skipped)} skipped (missing email)."
            ),
            details={"sent": sent, "skipped": skipped, "provider": "stub_or_configured"},
        )


class CalendarAutomation(AutomationModuleBase):
    module = AutomationModule.CALENDAR
    label = "Calendar & Booking"
    description = "Prepare tastings and meetings for confirmation before saving."

    def __init__(
        self,
        ai: AIService,
        calendar: Optional[CalendarService] = None,
    ) -> None:
        self._ai = ai
        self._calendar = calendar or StubCalendarService()
        self._db = get_supabase_admin()

    async def plan_and_draft(
        self, *, user_id: str | UUID, prompt: str, knowledge: str = ""
    ) -> DraftBundle:
        today = datetime.utcnow().date().isoformat()
        system = (
            "Extract a calendar booking. Return ONLY JSON: "
            '{"plan":"...", "event":{"title":"","description":"","starts_at":"ISO8601",'
            '"ends_at":"ISO8601|null","location":"","guests":[]}} '
            f"Today is {today} UTC. If relative dates like 'next Friday', resolve them."
        )
        raw = await self._ai.complete_task(
            system,
            prompt,
            temperature=0.2,
        )
        data = _extract_json(raw)
        event = data.get("event") if isinstance(data, dict) else data
        if not event.get("starts_at"):
            # fallback next Friday 18:00
            d = datetime.utcnow()
            days = (4 - d.weekday()) % 7 or 7
            start = (d + timedelta(days=days)).replace(
                hour=18, minute=0, second=0, microsecond=0
            )
            event = {
                "title": event.get("title") or "Tequila tasting",
                "description": event.get("description") or prompt,
                "starts_at": start.isoformat() + "Z",
                "ends_at": (start + timedelta(hours=2)).isoformat() + "Z",
                "location": event.get("location") or "",
                "guests": event.get("guests") or [],
            }
        item = DraftItem(
            item_type="booking",
            title=event.get("title") or "Booking",
            content=event,
            sort_order=0,
        )
        return DraftBundle(
            title="Booking ready",
            plan_summary=data.get("plan")
            if isinstance(data, dict)
            else "Booking summary prepared for confirmation.",
            items=[item],
            preview={
                "confirmation_prompt": "Booking Ready. Confirm to save this booking?",
                "event": event,
            },
        )

    async def execute(
        self,
        *,
        user_id: str | UUID,
        run_id: str | UUID,
        items: List[dict],
        preview: Dict[str, Any],
    ) -> ExecuteResult:
        if not items:
            return ExecuteResult(summary="No booking to confirm.")
        content = items[0].get("content") or {}
        external = await self._calendar.create_event(
            CalendarEventPayload(
                title=content.get("title") or "Event",
                starts_at=content.get("starts_at") or "",
                ends_at=content.get("ends_at"),
                description=content.get("description"),
                location=content.get("location"),
                guests=content.get("guests") or [],
            )
        )
        row = (
            self._db.table("bookings")
            .insert(
                {
                    "user_id": str(user_id),
                    "run_id": str(run_id),
                    "title": content.get("title") or "Event",
                    "description": content.get("description"),
                    "starts_at": content.get("starts_at"),
                    "ends_at": content.get("ends_at"),
                    "location": content.get("location"),
                    "guests": content.get("guests") or [],
                    "status": "confirmed",
                    "external_calendar_id": external.get("id"),
                }
            )
            .execute()
        )
        return ExecuteResult(
            summary="Booking confirmed and saved.",
            details={"booking": (row.data or [None])[0], "calendar": external},
        )


class MarketingAutomation(AutomationModuleBase):
    module = AutomationModule.MARKETING
    label = "Marketing Automation"
    description = "Generate multi-channel weekly marketing content into a review library."

    def __init__(self, ai: AIService) -> None:
        self._ai = ai
        self._db = get_supabase_admin()

    async def plan_and_draft(
        self, *, user_id: str | UUID, prompt: str, knowledge: str = ""
    ) -> DraftBundle:
        channels = [
            "instagram",
            "facebook",
            "linkedin",
            "twitter",
            "email_newsletter",
            "blog",
            "video_script",
        ]
        system = (
            "You are L.U.C.E.R.O marketing lead for Blue Prince21 McKinzy / 759 Tequila. "
            "Return ONLY JSON: {\"plan\":\"...\",\"assets\":[{\"channel\":\"instagram\","
            "\"title\":\"...\",\"body\":\"...\"}]} "
            f"Include one asset for each: {', '.join(channels)}."
        )
        raw = await self._ai.complete_task(
            system,
            f"{prompt}\n\nBrand knowledge:\n{knowledge[:5000]}",
            temperature=0.55,
        )
        data = _extract_json(raw)
        assets = data.get("assets") if isinstance(data, dict) else data
        items = [
            DraftItem(
                item_type="marketing",
                title=f"{a.get('channel', 'channel').title()}: {a.get('title') or 'Draft'}",
                content={
                    "channel": a.get("channel") or "general",
                    "title": a.get("title") or "",
                    "body": a.get("body") or "",
                },
                sort_order=i,
            )
            for i, a in enumerate(assets or [])
        ]
        return DraftBundle(
            title="Weekly marketing pack",
            plan_summary=data.get("plan")
            if isinstance(data, dict)
            else f"Prepared {len(items)} marketing drafts.",
            items=items,
            preview={
                "confirmation_prompt": "Review complete. Save these assets to the Marketing Library?",
                "channels": [i.content.get("channel") for i in items],
            },
        )

    async def execute(
        self,
        *,
        user_id: str | UUID,
        run_id: str | UUID,
        items: List[dict],
        preview: Dict[str, Any],
    ) -> ExecuteResult:
        saved = []
        for item in items:
            content = item.get("content") or {}
            row = (
                self._db.table("marketing_assets")
                .insert(
                    {
                        "user_id": str(user_id),
                        "run_id": str(run_id),
                        "channel": content.get("channel") or "general",
                        "title": content.get("title") or item.get("title") or "Asset",
                        "body": content.get("body") or "",
                        "metadata": {},
                    }
                )
                .execute()
            )
            saved.append((row.data or [None])[0])
        return ExecuteResult(
            summary=f"Saved {len(saved)} assets to Marketing Library.",
            details={"assets": saved},
        )


class ResearchAutomation(AutomationModuleBase):
    module = AutomationModule.RESEARCH
    label = "Research Automation"
    description = "Produce executive research reports with recommendations and next steps."

    def __init__(self, ai: AIService) -> None:
        self._ai = ai
        self._db = get_supabase_admin()

    async def plan_and_draft(
        self, *, user_id: str | UUID, prompt: str, knowledge: str = ""
    ) -> DraftBundle:
        system = (
            "Write an executive research report in markdown with sections: "
            "Executive Summary, Top Companies, Recommendations, Next Steps. "
            "Return ONLY JSON: {\"plan\":\"...\",\"title\":\"...\",\"markdown\":\"...\"}."
        )
        raw = await self._ai.complete_task(
            system,
            f"{prompt}\n\nKnowledge / research context:\n{knowledge[:8000]}",
            temperature=0.4,
        )
        data = _extract_json(raw)
        title = data.get("title") or "Research Report"
        md = data.get("markdown") or raw
        return DraftBundle(
            title=title,
            plan_summary=data.get("plan") or "Research draft ready for approval.",
            items=[
                DraftItem(
                    item_type="report",
                    title=title,
                    content={"markdown": md, "report_type": "research"},
                    sort_order=0,
                )
            ],
            preview={
                "confirmation_prompt": "Approve to save this research report?",
                "markdown_preview": md[:1200],
            },
        )

    async def execute(
        self,
        *,
        user_id: str | UUID,
        run_id: str | UUID,
        items: List[dict],
        preview: Dict[str, Any],
    ) -> ExecuteResult:
        content = (items[0].get("content") if items else {}) or {}
        row = (
            self._db.table("automation_reports")
            .insert(
                {
                    "user_id": str(user_id),
                    "run_id": str(run_id),
                    "report_type": "research",
                    "title": items[0].get("title") if items else "Research Report",
                    "markdown": content.get("markdown") or "",
                }
            )
            .execute()
        )
        return ExecuteResult(
            summary="Research report saved (PDF-ready markdown).",
            details={"report": (row.data or [None])[0]},
        )


class ReportAutomation(AutomationModuleBase):
    module = AutomationModule.REPORT
    label = "Report Generation"
    description = "Generate executive business performance and pipeline reports."

    def __init__(self, ai: AIService) -> None:
        self._ai = ai
        self._db = get_supabase_admin()

    async def plan_and_draft(
        self, *, user_id: str | UUID, prompt: str, knowledge: str = ""
    ) -> DraftBundle:
        system = (
            "Create an executive report in markdown covering: Business Performance, "
            "Marketing Progress, Distributor Status, Investor Pipeline, Tasks, Risks, "
            "Recommendations. Return ONLY JSON "
            '{"plan":"...","title":"...","markdown":"..."}.'
        )
        raw = await self._ai.complete_task(
            system,
            f"{prompt}\n\nBusiness context:\n{knowledge[:8000]}",
            temperature=0.35,
        )
        data = _extract_json(raw)
        title = data.get("title") or "Executive Business Report"
        md = data.get("markdown") or raw
        return DraftBundle(
            title=title,
            plan_summary=data.get("plan") or "Executive report draft ready.",
            items=[
                DraftItem(
                    item_type="report",
                    title=title,
                    content={"markdown": md, "report_type": "executive"},
                )
            ],
            preview={
                "confirmation_prompt": "Approve to save this executive report?",
                "markdown_preview": md[:1200],
            },
        )

    async def execute(
        self,
        *,
        user_id: str | UUID,
        run_id: str | UUID,
        items: List[dict],
        preview: Dict[str, Any],
    ) -> ExecuteResult:
        content = (items[0].get("content") if items else {}) or {}
        row = (
            self._db.table("automation_reports")
            .insert(
                {
                    "user_id": str(user_id),
                    "run_id": str(run_id),
                    "report_type": "executive",
                    "title": items[0].get("title") if items else "Executive Report",
                    "markdown": content.get("markdown") or "",
                }
            )
            .execute()
        )
        return ExecuteResult(
            summary="Executive report saved.",
            details={"report": (row.data or [None])[0]},
        )


class SupportAutomation(AutomationModuleBase):
    module = AutomationModule.SUPPORT
    label = "Customer Support"
    description = "Draft customer reply messages for review before sending."

    def __init__(
        self,
        ai: AIService,
        messaging: Optional[MessagingService] = None,
    ) -> None:
        self._ai = ai
        self._messaging = messaging or StubMessagingService()

    async def plan_and_draft(
        self, *, user_id: str | UUID, prompt: str, knowledge: str = ""
    ) -> DraftBundle:
        system = (
            "Draft customer support replies for 759 / Blue Prince21 McKinzy. "
            "Return ONLY JSON: {\"plan\":\"...\",\"replies\":[{\"customer\":\"\","
            "\"channel\":\"email\",\"subject\":\"\",\"body\":\"\"}]}."
        )
        raw = await self._ai.complete_task(
            system,
            f"{prompt}\n\nFAQ / brand knowledge:\n{knowledge[:5000]}",
            temperature=0.4,
        )
        data = _extract_json(raw)
        replies = data.get("replies") if isinstance(data, dict) else data
        items = [
            DraftItem(
                item_type="support_reply",
                title=f"Reply to {r.get('customer') or 'customer'}",
                content={
                    "customer": r.get("customer") or "Customer",
                    "channel": r.get("channel") or "email",
                    "subject": r.get("subject") or "",
                    "body": r.get("body") or "",
                },
                sort_order=i,
            )
            for i, r in enumerate(replies or [])
        ]
        if not items:
            items = [
                DraftItem(
                    item_type="support_reply",
                    title="General customer reply",
                    content={
                        "customer": "Customer",
                        "channel": "email",
                        "subject": "Thank you for contacting 759",
                        "body": "Thank you for your message. Our team will follow up shortly.",
                    },
                )
            ]
        return DraftBundle(
            title="Customer support drafts",
            plan_summary=data.get("plan")
            if isinstance(data, dict)
            else "Support replies ready for approval.",
            items=items,
            preview={
                "confirmation_prompt": "Review complete. Approve before sending these replies?",
            },
        )

    async def execute(
        self,
        *,
        user_id: str | UUID,
        run_id: str | UUID,
        items: List[dict],
        preview: Dict[str, Any],
    ) -> ExecuteResult:
        results = []
        for item in items:
            content = item.get("content") or {}
            results.append(
                await self._messaging.send_message(
                    content.get("channel") or "email",
                    content.get("customer") or "customer",
                    content.get("body") or "",
                )
            )
        return ExecuteResult(
            summary=f"Queued {len(results)} support replies (provider stub until connected).",
            details={"results": results},
        )


class CrmAutomation(AutomationModuleBase):
    module = AutomationModule.CRM
    label = "CRM Management"
    description = "Prioritize contacts and recommend follow-up actions."

    def __init__(self, ai: AIService) -> None:
        self._ai = ai

    async def plan_and_draft(
        self, *, user_id: str | UUID, prompt: str, knowledge: str = ""
    ) -> DraftBundle:
        contacts = load_crm_contacts()
        # deterministic buckets first
        high, medium, low = [], [], []
        for c in contacts:
            p = (c.get("priority") or "").upper()
            if p in {"HOT", "HIGH"}:
                high.append(c)
            elif p in {"MEDIUM", "MED"}:
                medium.append(c)
            else:
                low.append(c)

        system = (
            "Given prioritized CRM contacts, return ONLY JSON: "
            '{"plan":"...","followups":[{"company":"","priority":"High|Medium|Low",'
            '"action":"...","why":"..."}]} with actionable follow-ups for top contacts.'
        )
        raw = await self._ai.complete_task(
            system,
            (
                f"{prompt}\n\nHigh:\n{contacts_as_text(high, 12)}\n\n"
                f"Medium:\n{contacts_as_text(medium, 10)}\n\n"
                f"Low:\n{contacts_as_text(low, 8)}"
            ),
            temperature=0.3,
        )
        data = _extract_json(raw)
        followups = data.get("followups") if isinstance(data, dict) else []
        items = [
            DraftItem(
                item_type="crm_bucket",
                title="High Priority",
                content={"priority": "High", "contacts": high[:15]},
                sort_order=0,
            ),
            DraftItem(
                item_type="crm_bucket",
                title="Medium Priority",
                content={"priority": "Medium", "contacts": medium[:15]},
                sort_order=1,
            ),
            DraftItem(
                item_type="crm_bucket",
                title="Low Priority",
                content={"priority": "Low", "contacts": low[:15]},
                sort_order=2,
            ),
            DraftItem(
                item_type="crm_followups",
                title="Recommended follow-ups",
                content={"followups": followups or []},
                sort_order=3,
            ),
        ]
        return DraftBundle(
            title="CRM prioritization",
            plan_summary=data.get("plan")
            if isinstance(data, dict)
            else "CRM contacts organized by priority.",
            items=items,
            preview={
                "confirmation_prompt": "Approve to save this CRM prioritization snapshot?",
                "counts": {
                    "high": len(high),
                    "medium": len(medium),
                    "low": len(low),
                },
            },
        )

    async def execute(
        self,
        *,
        user_id: str | UUID,
        run_id: str | UUID,
        items: List[dict],
        preview: Dict[str, Any],
    ) -> ExecuteResult:
        # Snapshot already persisted on the run; execution marks approved organization complete.
        return ExecuteResult(
            summary="CRM prioritization saved to automation history.",
            details={"items": len(items), "counts": preview.get("counts") or {}},
        )


def build_modules(ai: AIService) -> Dict[AutomationModule, AutomationModuleBase]:
    return {
        AutomationModule.EMAIL: EmailAutomation(ai),
        AutomationModule.CALENDAR: CalendarAutomation(ai),
        AutomationModule.MARKETING: MarketingAutomation(ai),
        AutomationModule.RESEARCH: ResearchAutomation(ai),
        AutomationModule.REPORT: ReportAutomation(ai),
        AutomationModule.SUPPORT: SupportAutomation(ai),
        AutomationModule.CRM: CrmAutomation(ai),
    }
