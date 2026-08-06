from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.dependencies import get_document_service
from app.core.security import CurrentUser, get_current_user
from app.models.schemas import DocumentOut, DocumentsResponse
from app.services.document_service import DocumentService

router = APIRouter(tags=["documents"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv", ".xlsx"}


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    documents: Annotated[DocumentService, Depends(get_document_service)],
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    lower = file.filename.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_UPLOAD_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {sorted(ALLOWED_UPLOAD_EXTENSIONS)}",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 25 MB limit")

    try:
        row = await documents.upload(
            user_id=user.id,
            filename=file.filename,
            file_bytes=data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Upload failed: {exc}"
        ) from exc

    return DocumentOut(**row)


@router.get("/documents", response_model=DocumentsResponse)
async def list_documents(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    documents: Annotated[DocumentService, Depends(get_document_service)],
):
    rows = documents.list_documents(user.id)
    return DocumentsResponse(documents=rows)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    documents: Annotated[DocumentService, Depends(get_document_service)],
):
    deleted = documents.delete_document(document_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return None
