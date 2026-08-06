"""Dashboard APIs for ZeroClaw / WhatsApp channel status and allowlist."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.database.repositories import (
    ChannelGatewayStatusRepository,
    ChannelIdentityRepository,
)

router = APIRouter(prefix="/channels", tags=["channels"])


class ChannelIdentityOut(BaseModel):
    id: UUID
    user_id: UUID
    channel: str
    external_id: str
    display_name: Optional[str] = None
    allowed: bool
    is_owner: bool = False
    last_message_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ChannelIdentityCreate(BaseModel):
    channel: str = "whatsapp"
    external_id: str = Field(..., min_length=3, max_length=128)
    display_name: Optional[str] = None
    allowed: bool = True
    is_owner: bool = False
    user_id: Optional[UUID] = None


class ChannelIdentityUpdate(BaseModel):
    display_name: Optional[str] = None
    allowed: Optional[bool] = None
    is_owner: Optional[bool] = None


class ChannelStatusOut(BaseModel):
    bridge_enabled: bool
    bridge_configured: bool
    gateway_online: bool
    whatsapp_linked: bool
    last_heartbeat_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    last_external_id: Optional[str] = None
    default_agent: str
    allowed_numbers: List[str]
    identities: List[ChannelIdentityOut]
    pairing_docs: str = (
        "Run scripts/start-zeroclaw.ps1, scan the QR from WhatsApp → "
        "Linked Devices, then message an allowlisted number."
    )


class GatewayHeartbeatIn(BaseModel):
    online: bool = True
    whatsapp_linked: bool = False
    meta: Optional[dict] = None


@router.get("/status", response_model=ChannelStatusOut)
async def channel_status(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    identities_repo = ChannelIdentityRepository()
    gateway_repo = ChannelGatewayStatusRepository()
    try:
        rows = identities_repo.list_for_channel("whatsapp")
    except Exception:
        rows = []
    try:
        gateway = gateway_repo.get() or {}
    except Exception:
        gateway = {}

    identities = []
    for r in rows:
        try:
            identities.append(
                ChannelIdentityOut(
                    id=r["id"],
                    user_id=r["user_id"],
                    channel=r["channel"],
                    external_id=r["external_id"],
                    display_name=r.get("display_name"),
                    allowed=bool(r.get("allowed")),
                    is_owner=bool(r.get("is_owner")),
                    last_message_at=r.get("last_message_at"),
                    created_at=r.get("created_at"),
                )
            )
        except Exception:
            continue

    allowed = [i.external_id for i in identities if i.allowed]
    return ChannelStatusOut(
        bridge_enabled=bool(settings.enable_channel_bridge),
        bridge_configured=bool(settings.lucero_channel_api_key),
        gateway_online=bool(gateway.get("online")),
        whatsapp_linked=bool(gateway.get("whatsapp_linked")),
        last_heartbeat_at=gateway.get("last_heartbeat_at"),
        last_message_at=gateway.get("last_message_at"),
        last_external_id=gateway.get("last_external_id"),
        default_agent=settings.channel_default_agent or "support",
        allowed_numbers=allowed,
        identities=identities,
    )


@router.get("/identities", response_model=List[ChannelIdentityOut])
async def list_identities(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    channel: Optional[str] = None,
):
    repo = ChannelIdentityRepository()
    try:
        rows = repo.list_for_channel(channel)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "channel_identities table missing — run "
                "migrations/004_channel_identities.sql in Supabase. "
                f"({exc})"
            ),
        ) from exc
    return [
        ChannelIdentityOut(
            id=r["id"],
            user_id=r["user_id"],
            channel=r["channel"],
            external_id=r["external_id"],
            display_name=r.get("display_name"),
            allowed=bool(r.get("allowed")),
            is_owner=bool(r.get("is_owner")),
            last_message_at=r.get("last_message_at"),
            created_at=r.get("created_at"),
        )
        for r in rows
    ]


@router.post("/identities", response_model=ChannelIdentityOut)
async def create_identity(
    body: ChannelIdentityCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    from app.database.client import get_supabase_admin
    from app.database.repositories import _normalize_external_id

    db = get_supabase_admin()
    external = _normalize_external_id(body.external_id)
    payload = {
        "user_id": str(body.user_id or user.id),
        "channel": body.channel.strip().lower(),
        "external_id": external,
        "display_name": body.display_name,
        "allowed": body.allowed,
        "is_owner": body.is_owner,
    }
    try:
        result = db.table("channel_identities").insert(payload).execute()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result.data:
        raise HTTPException(status_code=400, detail="Insert failed")
    r = result.data[0]
    return ChannelIdentityOut(
        id=r["id"],
        user_id=r["user_id"],
        channel=r["channel"],
        external_id=r["external_id"],
        display_name=r.get("display_name"),
        allowed=bool(r.get("allowed")),
        is_owner=bool(r.get("is_owner")),
        last_message_at=r.get("last_message_at"),
        created_at=r.get("created_at"),
    )


@router.patch("/identities/{identity_id}", response_model=ChannelIdentityOut)
async def update_identity(
    identity_id: UUID,
    body: ChannelIdentityUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    from app.database.client import get_supabase_admin

    db = get_supabase_admin()
    updates = {
        k: v
        for k, v in body.model_dump().items()
        if v is not None
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No updates")
    result = (
        db.table("channel_identities")
        .update(updates)
        .eq("id", str(identity_id))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Identity not found")
    r = result.data[0]
    return ChannelIdentityOut(
        id=r["id"],
        user_id=r["user_id"],
        channel=r["channel"],
        external_id=r["external_id"],
        display_name=r.get("display_name"),
        allowed=bool(r.get("allowed")),
        is_owner=bool(r.get("is_owner")),
        last_message_at=r.get("last_message_at"),
        created_at=r.get("created_at"),
    )


@router.delete("/identities/{identity_id}", status_code=204)
async def delete_identity(
    identity_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    from app.database.client import get_supabase_admin

    db = get_supabase_admin()
    db.table("channel_identities").delete().eq(
        "id", str(identity_id)
    ).execute()
    return None


@router.post("/heartbeat")
async def gateway_heartbeat(
    body: GatewayHeartbeatIn,
    _: Annotated[None, Depends(get_current_user)],
):
    """Optional: dashboard or start script can mark ZeroClaw online."""
    repo = ChannelGatewayStatusRepository()
    try:
        row = repo.upsert(
            online=body.online,
            whatsapp_linked=body.whatsapp_linked,
            meta=body.meta,
            heartbeat=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Gateway status unavailable: {exc}",
        ) from exc
    return {"ok": True, "status": row}
