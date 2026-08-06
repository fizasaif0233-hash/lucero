from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.core.dependencies import get_chat_service, get_history_service
from app.core.security import CurrentUser, get_current_user
from app.models.schemas import ChatRequest, ConversationDetailOut, HistoryResponse, MessageOut
from app.services.chat_service import ChatService
from app.services.document_service import HistoryService

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Stream a chat completion via Server-Sent Events."""

    async def event_generator():
        async for event in chat_service.stream_chat(
            user_id=user.id,
            message=body.message,
            conversation_id=body.conversation_id,
            model=body.model,
            regenerate_message_id=body.regenerate_message_id,
            agent_id=body.agent_id,
        ):
            yield event

    return EventSourceResponse(event_generator())


@router.get("/history", response_model=HistoryResponse)
async def list_history(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    history: Annotated[HistoryService, Depends(get_history_service)],
):
    conversations = history.list_conversations(user.id)
    return HistoryResponse(conversations=conversations)


@router.get("/history/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    history: Annotated[HistoryService, Depends(get_history_service)],
):
    detail = history.get_conversation(conversation_id, user.id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return ConversationDetailOut(
        **{k: detail[k] for k in ("id", "title", "model", "created_at", "updated_at")},
        messages=[MessageOut(**m) for m in detail.get("messages", [])],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    history: Annotated[HistoryService, Depends(get_history_service)],
):
    deleted = history.delete_conversation(conversation_id, user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return None
