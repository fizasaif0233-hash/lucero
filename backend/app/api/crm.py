"""CRM customers + profile timeline."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.models.ops_schemas import (
    BookingOut,
    CrmActivityOut,
    CustomerListResponse,
    CustomerOut,
    CustomerProfileOut,
)
from app.services.booking_service import booking_to_out
from app.services.crm_service import CrmService

router = APIRouter(prefix="/crm", tags=["crm"])


def get_crm_service() -> CrmService:
    return CrmService()


@router.get("/customers", response_model=CustomerListResponse)
async def list_customers(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    crm: Annotated[CrmService, Depends(get_crm_service)],
):
    rows = crm.list_customers(user.id)
    return CustomerListResponse(customers=[CustomerOut(**r) for r in rows])


@router.get("/customers/{customer_id}", response_model=CustomerProfileOut)
async def customer_profile(
    customer_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    crm: Annotated[CrmService, Depends(get_crm_service)],
):
    profile = crm.get_profile(user.id, str(customer_id))
    return CustomerProfileOut(
        customer=CustomerOut(**profile["customer"]),
        bookings=[BookingOut(**booking_to_out(b)) for b in profile["bookings"]],
        email_history=profile["email_history"],
        timeline=[CrmActivityOut(**a) for a in profile["timeline"]],
    )
