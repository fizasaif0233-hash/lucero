from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_memory_service
from app.core.security import CurrentUser, get_current_user
from app.models.schemas import MemoryCreate, MemoryOut, UserOut
from app.services.document_service import MemoryService
from app.utils.mappers import to_user_out

router = APIRouter(tags=["memory"])


@router.get("/me", response_model=UserOut)
async def me(user: Annotated[CurrentUser, Depends(get_current_user)]):
    return to_user_out(user)


@router.get("/memory", response_model=List[MemoryOut])
async def list_memory(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    memory: Annotated[MemoryService, Depends(get_memory_service)],
):
    return memory.list_memory(user.id)


@router.post("/memory", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
async def create_memory(
    body: MemoryCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    memory: Annotated[MemoryService, Depends(get_memory_service)],
):
    return await memory.create_memory(
        user_id=user.id,
        content=body.content,
        key=body.key,
        category=body.category,
    )


@router.delete("/memory/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    memory: Annotated[MemoryService, Depends(get_memory_service)],
):
    deleted = memory.delete_memory(memory_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return None
