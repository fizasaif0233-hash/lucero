"""Reminder list + manual/cron run endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.models.ops_schemas import (
    ReminderListResponse,
    ReminderOut,
    ReminderRunResponse,
)
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["reminders"])


def get_reminder_service() -> ReminderService:
    return ReminderService()


@router.get("", response_model=ReminderListResponse)
async def list_reminders(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    reminders: Annotated[ReminderService, Depends(get_reminder_service)],
):
    rows = await reminders.list_for_user(user.id)
    return ReminderListResponse(reminders=[ReminderOut(**r) for r in rows])


@router.post("/run", response_model=ReminderRunResponse)
async def run_reminders(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    reminders: Annotated[ReminderService, Depends(get_reminder_service)],
):
    """Process due reminders (call from cron or dashboard). Auth required."""
    _ = user  # authenticated owners only
    result = await reminders.run_due()
    return ReminderRunResponse(**result)
