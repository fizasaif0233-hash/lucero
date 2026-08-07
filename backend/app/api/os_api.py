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


@router.get("/assets/{asset_id}/download")
async def download_asset(
    asset_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    jobs: Annotated[JobService, Depends(get_job_service)],
):
    """Proxy file bytes with Content-Disposition so the browser saves (not navigates)."""
    import httpx
    from fastapi.responses import Response

    asset = jobs.get_asset(asset_id, user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    url = asset.get("public_url")
    if not url:
        raise HTTPException(status_code=404, detail="Asset has no file URL")
    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.content
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not fetch asset file: {exc}"
        ) from exc

    mime = asset.get("mime") or "application/octet-stream"
    kind = (asset.get("kind") or "").lower()
    title = (asset.get("title") or "lucero-asset").replace('"', "")
    ext = "bin"
    if "pdf" in mime or kind == "pdf":
        ext = "pdf"
    elif "png" in mime or kind == "image":
        ext = "png"
    elif "jpeg" in mime or "jpg" in mime:
        ext = "jpg"
    elif "mp4" in mime or kind == "video":
        ext = "mp4"
    elif "audio" in mime or kind == "audio":
        ext = "mp3"
    filename = f"{title[:80].replace(' ', '-')}.{ext}"
    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, max-age=60",
        },
    )


@router.get("/download-by-url")
async def download_by_url(
    url: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    filename: Optional[str] = None,
):
    """Proxy any allowed storage URL as an attachment so the browser saves the file."""
    import httpx
    from urllib.parse import urlparse
    from fastapi.responses import Response
    from app.core.config import get_settings

    settings = get_settings()
    parsed = urlparse(url)
    allowed_host = urlparse(settings.supabase_url).netloc.lower()
    host = (parsed.netloc or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        raise HTTPException(status_code=400, detail="Invalid URL")
    # Only allow our Supabase storage (or Replicate delivery hosts used briefly)
    ok = host == allowed_host or host.endswith(".supabase.co") or "replicate.delivery" in host
    if not ok:
        raise HTTPException(status_code=403, detail="URL host not allowed for download")

    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.content
            mime = resp.headers.get("content-type") or "application/octet-stream"
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not fetch file: {exc}"
        ) from exc

    name = (filename or "lucero-asset").replace('"', "").replace("/", "-")
    if "." not in name:
        if "pdf" in mime:
            name += ".pdf"
        elif "png" in mime:
            name += ".png"
        elif "jpeg" in mime or "jpg" in mime:
            name += ".jpg"
        elif "mp4" in mime:
            name += ".mp4"
        else:
            name += ".bin"

    return Response(
        content=data,
        media_type=mime.split(";")[0].strip(),
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "private, max-age=60",
        },
    )


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
