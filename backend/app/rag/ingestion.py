import re
import tempfile
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from app.ai.service import AIService
from app.core.config import Settings, get_settings
from app.database.client import get_supabase_admin
from app.rag.chunker import DocumentChunker
from app.rag.extractors import LangChainTextExtractor
from app.rag.retriever import Retriever
from app.utils.logging import get_logger

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {"pdf", "txt", "docx", "csv", "xlsx"}
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "web": "text/plain",
}


def _safe_storage_name(name: str, *, fallback: str = "document") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return (cleaned or fallback)[:120]



class IngestionService:
    """Upload / text / website → chunk → embed → store pipeline."""

    def __init__(
        self,
        ai_service: AIService,
        settings: Optional[Settings] = None,
        extractor: Optional[LangChainTextExtractor] = None,
        chunker: Optional[DocumentChunker] = None,
    ) -> None:
        self._ai = ai_service
        self._settings = settings or get_settings()
        self._extractor = extractor or LangChainTextExtractor()
        self._chunker = chunker or DocumentChunker(self._settings)
        self._db = get_supabase_admin()

    async def ingest_upload(
        self,
        *,
        user_id: str | UUID,
        filename: str,
        file_bytes: bytes,
        source_type: str = "upload",
        is_shared: bool = False,
        source_url: Optional[str] = None,
    ) -> dict:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
            )

        user_id_str = str(user_id)
        safe_name = Path(filename).name
        storage_path = f"{user_id_str}/{safe_name}"

        document = self._create_document_row(
            user_id=user_id_str,
            filename=safe_name,
            original_filename=safe_name,
            file_type=ext,
            storage_path=storage_path,
            file_size=len(file_bytes),
            source_type=source_type,
            source_url=source_url,
            is_shared=is_shared,
        )
        document_id = document["id"]

        try:
            self._db.storage.from_(self._settings.storage_bucket).upload(
                path=storage_path,
                file=file_bytes,
                file_options={
                    "content-type": CONTENT_TYPES.get(ext, "application/octet-stream"),
                    "upsert": "true",
                },
            )
            text = await self._extract_bytes(file_bytes, ext)
            return await self._finalize_chunks(
                document_id=document_id,
                user_id=user_id_str,
                text=text,
                metadata={
                    "filename": safe_name,
                    "document_name": safe_name,
                    "original_filename": safe_name,
                    "file_type": ext,
                    "source_type": source_type,
                    "source_url": source_url,
                },
                is_shared=is_shared,
            )
        except Exception as exc:
            self._mark_failed(document_id, exc)
            raise

    async def ingest_text(
        self,
        *,
        user_id: str | UUID,
        title: str,
        text: str,
        source_type: str = "asset",
        source_url: Optional[str] = None,
        is_shared: bool = True,
        file_type: str = "txt",
    ) -> dict:
        """Ingest raw text (Assets notes or crawled website pages)."""
        if not text or not text.strip():
            raise ValueError("Empty text")

        user_id_str = str(user_id)
        safe_name = _safe_storage_name(Path(title).name.replace("/", "-"), fallback="page")
        storage_path = f"{user_id_str}/text/{safe_name}_{uuid4().hex[:8]}.txt"
        file_bytes = text.encode("utf-8")

        document = self._create_document_row(
            user_id=user_id_str,
            filename=f"{safe_name}.txt",
            original_filename=f"{safe_name}.txt",
            file_type=file_type if file_type in {"txt", "web"} else "txt",
            storage_path=storage_path,
            file_size=len(file_bytes),
            source_type=source_type,
            source_url=source_url,
            is_shared=is_shared,
        )
        document_id = document["id"]

        try:
            self._db.storage.from_(self._settings.storage_bucket).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": "text/plain", "upsert": "true"},
            )
            return await self._finalize_chunks(
                document_id=document_id,
                user_id=user_id_str,
                text=text,
                metadata={
                    "filename": f"{safe_name}.txt",
                    "document_name": title if "." in title else f"{safe_name}.txt",
                    "original_filename": f"{safe_name}.txt",
                    "file_type": file_type,
                    "source_type": source_type,
                    "source_url": source_url,
                    "title": title,
                },
                is_shared=is_shared,
            )
        except Exception as exc:
            self._mark_failed(document_id, exc)
            raise

    def _create_document_row(
        self,
        *,
        user_id: str,
        filename: str,
        original_filename: str,
        file_type: str,
        storage_path: str,
        file_size: int,
        source_type: str,
        source_url: Optional[str],
        is_shared: bool,
    ) -> dict:
        result = (
            self._db.table("business_documents")
            .insert(
                {
                    "user_id": user_id,
                    "filename": filename,
                    "original_filename": original_filename,
                    "file_type": file_type,
                    "storage_path": storage_path,
                    "file_size": file_size,
                    "status": "processing",
                    "source_type": source_type,
                    "source_url": source_url,
                    "is_shared": is_shared,
                }
            )
            .execute()
        )
        return result.data[0]

    async def _finalize_chunks(
        self,
        *,
        document_id: str,
        user_id: str,
        text: str,
        metadata: dict,
        is_shared: bool,
    ) -> dict:
        chunks = self._chunker.split(text)
        if not chunks:
            raise ValueError("Document produced no chunks")

        embeddings = await self._ai.embed_texts(chunks)
        doc_name = (
            metadata.get("document_name")
            or metadata.get("original_filename")
            or metadata.get("filename")
            or "document"
        )
        rows = [
            {
                "document_id": document_id,
                "user_id": user_id,
                "chunk_index": idx,
                "content": chunk,
                "embedding": embeddings[idx],
                "metadata": {
                    **metadata,
                    "document_name": doc_name,
                    "original_filename": doc_name,
                    "chunk_index": idx,
                    "section": Retriever.infer_section(chunk),
                },
                "is_shared": is_shared,
            }
            for idx, chunk in enumerate(chunks)
        ]

        batch_size = 50
        for i in range(0, len(rows), batch_size):
            self._db.table("document_chunks").insert(rows[i : i + batch_size]).execute()

        updated = (
            self._db.table("business_documents")
            .update({"status": "ready", "chunk_count": len(chunks)})
            .eq("id", document_id)
            .execute()
        )
        logger.info(
            "document_ingested",
            document_id=document_id,
            chunks=len(chunks),
            shared=is_shared,
            source_type=metadata.get("source_type"),
        )
        return updated.data[0]

    def _mark_failed(self, document_id: str, exc: Exception) -> None:
        logger.exception("document_ingest_failed", document_id=document_id)
        self._db.table("business_documents").update(
            {"status": "failed", "error_message": str(exc)[:1000]}
        ).eq("id", document_id).execute()

    async def _extract_bytes(self, file_bytes: bytes, ext: str) -> str:
        suffix = f".{ext}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)
        try:
            return self._extractor.extract(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
