"""Email draft / approve / send API (Resend). Never auto-sends."""

from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.security import CurrentUser, get_current_user
from app.models.ops_schemas import (
    EmailDraftRequest,
    EmailListResponse,
    EmailLogListResponse,
    EmailLogOut,
    EmailOut,
    EmailSendRequest,
    EmailTemplateCreate,
    EmailTemplateListResponse,
    EmailTemplateOut,
    EmailUpdateRequest,
)
from app.services.lucero_email import LuceroEmailService

router = APIRouter(prefix="/email", tags=["email"])


def get_email_service() -> LuceroEmailService:
    return LuceroEmailService()


@router.post("/draft", response_model=EmailOut)
async def create_draft(
    body: EmailDraftRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    await emails.ensure_default_templates(user.id)
    row = await emails.create_draft(
        user.id,
        recipient=str(body.recipient),
        subject=body.subject,
        body_html=body.body_html,
        body_text=body.body_text,
        recipient_name=body.recipient_name,
        template_id=str(body.template_id) if body.template_id else None,
        customer_id=str(body.customer_id) if body.customer_id else None,
        booking_id=str(body.booking_id) if body.booking_id else None,
    )
    return EmailOut(**row)


@router.post("/send", response_model=EmailOut)
async def send_email(
    body: EmailSendRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    row = await emails.send_approved(user.id, body.email_id, confirm=body.confirm)
    return EmailOut(**row)


@router.post("/template", response_model=EmailTemplateOut)
async def create_template(
    body: EmailTemplateCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    row = await emails.create_template(user.id, body.model_dump())
    return EmailTemplateOut(**row)


@router.get("/templates", response_model=EmailTemplateListResponse)
async def list_templates(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    await emails.ensure_default_templates(user.id)
    rows = await emails.list_templates(user.id)
    return EmailTemplateListResponse(
        templates=[EmailTemplateOut(**r) for r in rows]
    )


@router.get("/history", response_model=EmailListResponse)
async def email_history(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
    folder: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    rows = await emails.list_emails(user.id, folder=folder, status_filter=status)
    return EmailListResponse(emails=[EmailOut(**r) for r in rows])


@router.get("/inbox", response_model=EmailListResponse)
async def email_inbox(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    pending = await emails.list_emails(user.id, status_filter="pending_approval")
    approved = await emails.list_emails(user.id, status_filter="approved")
    failed = await emails.list_emails(user.id, folder="failed")
    merged = {r["id"]: r for r in pending + approved + failed}
    return EmailListResponse(emails=[EmailOut(**r) for r in merged.values()])


@router.get("/logs", response_model=EmailLogListResponse)
async def email_logs(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    rows = await emails.list_logs(user.id)
    return EmailLogListResponse(logs=[EmailLogOut(**r) for r in rows])


@router.get("/{email_id}", response_model=EmailOut)
async def get_email(
    email_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    row = await emails.get(user.id, email_id)
    return EmailOut(**row)


@router.patch("/{email_id}", response_model=EmailOut)
async def edit_draft(
    email_id: UUID,
    body: EmailUpdateRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    row = await emails.update_draft(
        user.id, email_id, body.model_dump(exclude_unset=True)
    )
    return EmailOut(**row)


@router.post("/{email_id}/approve", response_model=EmailOut)
async def approve_email(
    email_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    row = await emails.approve(user.id, email_id)
    return EmailOut(**row)


@router.post("/{email_id}/cancel", response_model=EmailOut)
async def cancel_email(
    email_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    row = await emails.cancel(user.id, email_id)
    return EmailOut(**row)


@router.post("/{email_id}/retry", response_model=EmailOut)
async def retry_email(
    email_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    emails: Annotated[LuceroEmailService, Depends(get_email_service)],
):
    row = await emails.retry(user.id, email_id)
    return EmailOut(**row)
