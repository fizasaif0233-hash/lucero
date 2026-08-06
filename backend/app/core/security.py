from dataclasses import dataclass
from typing import Annotated, Any, Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import Settings, get_settings
from app.database.client import get_supabase_admin
from app.utils.logging import get_logger

security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    role: str
    full_name: Optional[str] = None


def _decode_local_jwt(token: str, settings: Settings) -> Optional[dict[str, Any]]:
    """Try legacy HS256 verification (works when project still uses JWT secret)."""
    attempts = [
        {"algorithms": ["HS256"], "audience": "authenticated"},
        {
            "algorithms": ["HS256"],
            "options": {"verify_aud": False},
        },
    ]
    for kwargs in attempts:
        try:
            return jwt.decode(token, settings.supabase_jwt_secret, **kwargs)
        except JWTError:
            continue
    return None


async def _verify_via_supabase_auth(
    token: str, settings: Settings
) -> Optional[dict[str, Any]]:
    """
    Validate access token with Supabase Auth.

    Works for both legacy HS256 and newer asymmetric signing keys.
    """
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.supabase_anon_key,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
        if response.status_code != 200:
            logger.warning(
                "supabase_auth_verify_failed",
                status=response.status_code,
                body=response.text[:200],
            )
            return None
        data = response.json()
        # Normalize to JWT-like claims used below
        return {
            "sub": data.get("id"),
            "email": data.get("email"),
            "user_metadata": data.get("user_metadata") or {},
        }
    except Exception as exc:
        logger.warning("supabase_auth_verify_error", error=str(exc))
        return None


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(security)
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    """Validate Supabase access token and resolve the authenticated user."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    payload = _decode_local_jwt(token, settings)
    if payload is None:
        payload = await _verify_via_supabase_auth(token, settings)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please sign out and sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims",
        )

    supabase = get_supabase_admin()
    result = (
        supabase.table("users")
        .select("id, email, role, full_name")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        meta = payload.get("user_metadata") or {}
        role = meta.get("role") or "owner"
        full_name = meta.get("full_name") or str(email).split("@")[0]
        insert = (
            supabase.table("users")
            .upsert(
                {
                    "id": user_id,
                    "email": email,
                    "role": role,
                    "full_name": full_name,
                }
            )
            .execute()
        )
        row = insert.data[0] if insert.data else {
            "id": user_id,
            "email": email,
            "role": role,
            "full_name": full_name,
        }
    else:
        row = result.data[0]

    return CurrentUser(
        id=row["id"],
        email=row["email"],
        role=row.get("role") or "owner",
        full_name=row.get("full_name"),
    )
