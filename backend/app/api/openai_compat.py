"""OpenAI-compatible /v1/chat/completions for ZeroClaw channel sidecar."""

from __future__ import annotations

from typing import Annotated, Any, List, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.dependencies import get_chat_service
from app.services.channel_bridge import ChannelBridgeService
from app.services.chat_service import ChatService

router = APIRouter(tags=["openai-compat"])
_bearer = HTTPBearer(auto_error=False)


class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Any], None] = None


class ChatCompletionsRequest(BaseModel):
    model: Optional[str] = "lucero/agents"
    messages: List[ChatMessage] = Field(default_factory=list)
    stream: bool = False
    user: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


def _require_channel_auth(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(_bearer)
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if not settings.enable_channel_bridge:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Channel bridge is disabled. Set ENABLE_CHANNEL_BRIDGE=true.",
        )
    expected = (settings.lucero_channel_api_key or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LUCERO_CHANNEL_API_KEY is not configured.",
        )
    token = credentials.credentials if credentials else ""
    if not token or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid channel API key",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_channel_bridge(
    chat: Annotated[ChatService, Depends(get_chat_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChannelBridgeService:
    return ChannelBridgeService(chat_service=chat, settings=settings)


@router.get("/models")
async def list_models(
    _: Annotated[None, Depends(_require_channel_auth)],
):
    return {
        "object": "list",
        "data": [
            {
                "id": "lucero/agents",
                "object": "model",
                "owned_by": "lucero",
            }
        ],
    }


@router.post("/chat/completions")
async def chat_completions(
    body: ChatCompletionsRequest,
    _: Annotated[None, Depends(_require_channel_auth)],
    bridge: Annotated[ChannelBridgeService, Depends(get_channel_bridge)],
    x_lucero_channel: Annotated[Optional[str], Header()] = None,
    x_lucero_external_id: Annotated[Optional[str], Header()] = None,
    x_channel_user: Annotated[Optional[str], Header()] = None,
):
    channel = (x_lucero_channel or "whatsapp").strip().lower()
    external_id = x_lucero_external_id or x_channel_user
    messages = [m.model_dump() for m in body.messages]

    if body.stream:
        return StreamingResponse(
            bridge.stream(
                messages=messages,
                channel=channel,
                external_id=external_id,
                body_user=body.user,
                model=body.model,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await bridge.complete(
        messages=messages,
        channel=channel,
        external_id=external_id,
        body_user=body.user,
        model=body.model,
    )
