"""OS jobs, assets, STT/TTS, and image tool APIs."""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.core.security import CurrentUser, get_current_user
from app.media.job_service import JobService
from app.media.stt import SpeechToText
from app.media.tts import TextToSpeech
from app.media.replicate_client import ReplicateError

router = APIRouter(prefix="/os", tags=["os"])


class JobCreate(BaseModel):
    task_type: str = Field(..., min_length=1, max_length=64)
    input: Dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[UUID] = None
    client_request_id: Optional[str] = None


class TtsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4500)
    voice: str = "af_bella"


class ImageToolRequest(BaseModel):
    image_url: Optional[str] = None
    prompt: Optional[str] = None
    conversation_id: Optional[UUID] = None


def get_job_service() -> JobService:
    return JobService()


@router.post("/jobs")
async def create_job(
    body: JobCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    jobs: Annotated[JobService, Depends(get_job_service)],
):
    try:
        job = jobs.create(
            user_id=user.id,
            task_type=body.task_type,
            input_data=body.input,
            conversation_id=body.conversation_id,
            client_request_id=body.client_request_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not create job (run migration 006_ai_os.sql?): {exc}",
        ) from exc
    return job


@router.get("/jobs")
async def list_jobs(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    jobs: Annotated[JobService, Depends(get_job_service)],
):
    return {"jobs": jobs.list_for_user(user.id)}


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    jobs: Annotated[JobService, Depends(get_job_service)],
):
    job = jobs.get(job_id, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/assets")
async def list_assets(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    jobs: Annotated[JobService, Depends(get_job_service)],
    job_id: Optional[UUID] = None,
):
    return {
        "assets": jobs.list_assets(
            user.id, job_id=str(job_id) if job_id else None
        )
    }


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    jobs: Annotated[JobService, Depends(get_job_service)],
):
    asset = jobs.get_asset(asset_id, user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/tts")
async def tts(
    body: TtsRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    jobs: Annotated[JobService, Depends(get_job_service)],
):
    job = jobs.create(
        user_id=user.id,
        task_type="tts",
        input_data={"text": body.text, "voice": body.voice},
    )
    # Process inline for snappy voice replies
    done = await jobs.process_job(job)
    return done


@router.post("/stt")
async def stt(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    data = await file.read()
    try:
        text = await SpeechToText().transcribe(audio_bytes=data, language=language)
    except ReplicateError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"text": text}


@router.post("/tools/upscale")
async def tool_upscale(
    body: ImageToolRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    jobs: Annotated[JobService, Depends(get_job_service)],
):
    if not body.image_url:
        raise HTTPException(status_code=400, detail="image_url required")
    job = jobs.create(
        user_id=user.id,
        task_type="upscale",
        input_data={"image_url": body.image_url},
        conversation_id=body.conversation_id,
    )
    return await jobs.process_job(job)


@router.post("/tools/remove-bg")
async def tool_remove_bg(
    body: ImageToolRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    jobs: Annotated[JobService, Depends(get_job_service)],
):
    if not body.image_url:
        raise HTTPException(status_code=400, detail="image_url required")
    job = jobs.create(
        user_id=user.id,
        task_type="remove_bg",
        input_data={"image_url": body.image_url},
        conversation_id=body.conversation_id,
    )
    return await jobs.process_job(job)


@router.post("/tools/variations")
async def tool_variations(
    body: ImageToolRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    jobs: Annotated[JobService, Depends(get_job_service)],
):
    job = jobs.create(
        user_id=user.id,
        task_type="variations",
        input_data={
            "prompt": body.prompt or "Luxury tequila brand visual variation",
            "image_url": body.image_url,
        },
        conversation_id=body.conversation_id,
    )
    return await jobs.process_job(job)
