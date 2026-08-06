from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_agent_orchestrator, get_chat_service
from app.core.security import CurrentUser, get_current_user
from app.agents.orchestrator import AgentOrchestrator
from app.models.schemas import (
    AgentCatalogResponse,
    AgentInfoOut,
    AgentAskRequest,
)
from app.services.chat_service import ChatService
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=AgentCatalogResponse)
async def list_agents(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    orchestrator: Annotated[AgentOrchestrator, Depends(get_agent_orchestrator)],
):
    return AgentCatalogResponse(
        agents=[AgentInfoOut(**a) for a in orchestrator.catalog()]
    )


@router.get("/{agent_id}", response_model=AgentInfoOut)
async def get_agent(
    agent_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    orchestrator: Annotated[AgentOrchestrator, Depends(get_agent_orchestrator)],
):
    agent = orchestrator.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    info = agent.info
    return AgentInfoOut(
        id=info.id,
        name=info.name,
        title=info.title,
        description=info.description,
        skills=list(info.skills),
        status=info.status,
        icon=info.icon,
    )


@router.post("/{agent_id}/chat")
async def agent_chat(
    agent_id: str,
    body: AgentAskRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    orchestrator: Annotated[AgentOrchestrator, Depends(get_agent_orchestrator)],
):
    """Force a turn through a specific specialist (Open Agent)."""
    if not orchestrator.get(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    async def event_generator():
        async for event in chat_service.stream_chat(
            user_id=user.id,
            message=body.message,
            conversation_id=body.conversation_id,
            model=body.model,
            agent_id=agent_id,
        ):
            yield event

    return EventSourceResponse(event_generator())
