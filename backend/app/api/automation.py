from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_automation_service
from app.core.security import CurrentUser, get_current_user
from app.models.schemas import (
    AutomationCatalogResponse,
    AutomationHistoryResponse,
    AutomationItemOut,
    AutomationItemUpdateRequest,
    AutomationModuleInfo,
    AutomationRunOut,
    AutomationStartRequest,
)
from app.automation.service import AutomationService

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/modules", response_model=AutomationCatalogResponse)
async def list_modules(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[AutomationService, Depends(get_automation_service)],
):
    return AutomationCatalogResponse(
        modules=[AutomationModuleInfo(**m) for m in service.catalog()]
    )


@router.post("/runs", response_model=AutomationRunOut)
async def start_run(
    body: AutomationStartRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[AutomationService, Depends(get_automation_service)],
):
    try:
        run = await service.start_run(
            user_id=user.id, module=body.module, prompt=body.prompt
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Automation failed: {exc}",
        )
    return AutomationRunOut(**run)


@router.get("/runs", response_model=AutomationHistoryResponse)
async def history(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[AutomationService, Depends(get_automation_service)],
    module: Optional[str] = Query(default=None),
):
    runs = service.history(user_id=user.id, module=module)
    return AutomationHistoryResponse(runs=runs)


@router.get("/runs/{run_id}", response_model=AutomationRunOut)
async def get_run(
    run_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[AutomationService, Depends(get_automation_service)],
):
    run = service.get_run(user_id=user.id, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return AutomationRunOut(**run)


@router.post("/runs/{run_id}/approve", response_model=AutomationRunOut)
async def approve_run(
    run_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[AutomationService, Depends(get_automation_service)],
):
    try:
        run = await service.approve_run(user_id=user.id, run_id=run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AutomationRunOut(**run)


@router.post("/runs/{run_id}/cancel", response_model=AutomationRunOut)
async def cancel_run(
    run_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[AutomationService, Depends(get_automation_service)],
):
    try:
        run = service.cancel_run(user_id=user.id, run_id=run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AutomationRunOut(**run)


@router.patch("/items/{item_id}", response_model=AutomationItemOut)
async def update_item(
    item_id: UUID,
    body: AutomationItemUpdateRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[AutomationService, Depends(get_automation_service)],
):
    item = service.update_item(
        user_id=user.id,
        item_id=item_id,
        content=body.content,
        title=body.title,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return AutomationItemOut(**item)
