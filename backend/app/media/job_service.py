"""Async AI job queue backed by Supabase ai_jobs / generated_assets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.core.config import Settings, get_settings
from app.database.client import get_supabase_admin
from app.media.pipelines import run_pipeline
from app.media.replicate_client import ReplicateError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class JobService:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._db = get_supabase_admin()

    def create(
        self,
        *,
        user_id: str | UUID,
        task_type: str,
        input_data: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str | UUID] = None,
        client_request_id: Optional[str] = None,
        pipeline: Optional[List[str]] = None,
    ) -> dict:
        if client_request_id:
            existing = (
                self._db.table("ai_jobs")
                .select("*")
                .eq("user_id", str(user_id))
                .eq("client_request_id", client_request_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                return existing.data[0]

        row = {
            "id": str(uuid4()),
            "user_id": str(user_id),
            "conversation_id": str(conversation_id) if conversation_id else None,
            "client_request_id": client_request_id,
            "task_type": task_type,
            "pipeline": pipeline or [task_type],
            "status": "queued",
            "progress": 0,
            "progress_detail": "Queued",
            "input": input_data or {},
            "result": {},
        }
        result = self._db.table("ai_jobs").insert(row).execute()
        return result.data[0]

    def get(self, job_id: str | UUID, user_id: str | UUID) -> Optional[dict]:
        result = (
            self._db.table("ai_jobs")
            .select("*")
            .eq("id", str(job_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def list_for_user(self, user_id: str | UUID, limit: int = 30) -> List[dict]:
        result = (
            self._db.table("ai_jobs")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def list_assets(
        self, user_id: str | UUID, *, job_id: Optional[str] = None, limit: int = 50
    ) -> List[dict]:
        q = (
            self._db.table("generated_assets")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(min(limit, 200))
        )
        if job_id:
            q = q.eq("job_id", job_id)
        return q.execute().data or []

    def get_asset(self, asset_id: str | UUID, user_id: str | UUID) -> Optional[dict]:
        result = (
            self._db.table("generated_assets")
            .select("*")
            .eq("id", str(asset_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def _update(self, job_id: str, **fields: Any) -> None:
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._db.table("ai_jobs").update(fields).eq("id", job_id).execute()

    def _save_asset(self, user_id: str, job_id: str, asset: Dict[str, Any]) -> dict:
        row = {
            "id": str(uuid4()),
            "user_id": user_id,
            "job_id": job_id,
            "kind": asset.get("kind") or "other",
            "title": asset.get("title") or "Asset",
            "storage_path": asset.get("storage_path") or "",
            "public_url": asset.get("public_url"),
            "mime": asset.get("mime") or "application/octet-stream",
            "byte_size": asset.get("byte_size"),
            "meta": asset.get("meta") or {},
        }
        result = self._db.table("generated_assets").insert(row).execute()
        return result.data[0]

    async def process_job(self, job: dict) -> dict:
        job_id = job["id"]
        user_id = job["user_id"]
        task_type = job["task_type"]
        input_data = job.get("input") or {}

        self._update(
            job_id,
            status="running",
            progress=5,
            progress_detail="Starting…",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        async def on_progress(pct: int, detail: str) -> None:
            self._update(job_id, progress=pct, progress_detail=detail)

        try:
            if (
                not self._settings.replicate_api_token
                and not self._settings.gemini_api_key
                and task_type
                in {
                    "commercial_video",
                    "video",
                    "logo",
                    "image",
                    "upscale",
                    "remove_bg",
                    "variations",
                    "tts",
                }
            ):
                raise ReplicateError(
                    "Set GEMINI_API_KEY (images) or REPLICATE_API_TOKEN on Railway "
                    "to enable this media type."
                )

            # Video/audio still need Replicate even when Gemini handles stills
            if (
                not self._settings.replicate_api_token
                and task_type
                in {
                    "commercial_video",
                    "video",
                    "upscale",
                    "remove_bg",
                    "tts",
                }
            ):
                raise ReplicateError(
                    "REPLICATE_API_TOKEN not configured. Add it on Railway to enable this media type."
                )

            result = await run_pipeline(
                task_type,
                user_id=user_id,
                input_data=input_data,
                settings=self._settings,
                on_progress=on_progress,
            )
            saved = []
            for asset in result.get("assets") or []:
                saved.append(self._save_asset(user_id, job_id, asset))

            out = {
                **result,
                "saved_assets": [
                    {
                        "id": a["id"],
                        "kind": a["kind"],
                        "title": a["title"],
                        "url": a.get("public_url"),
                        "mime": a.get("mime"),
                    }
                    for a in saved
                ],
            }
            self._update(
                job_id,
                status="succeeded",
                progress=100,
                progress_detail="Done",
                result=out,
                finished_at=datetime.now(timezone.utc).isoformat(),
                error_message=None,
            )
            return self.get(job_id, user_id) or job
        except Exception as exc:
            logger.exception("job_failed", job_id=job_id, error=str(exc))
            self._update(
                job_id,
                status="failed",
                progress=100,
                progress_detail="Failed",
                error_message=str(exc)[:1000],
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
            return self.get(job_id, user_id) or job

    async def process_next(self) -> Optional[dict]:
        """Claim one queued job (best-effort; service role)."""
        result = (
            self._db.table("ai_jobs")
            .select("*")
            .eq("status", "queued")
            .order("created_at")
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        job = result.data[0]
        # Optimistic claim
        claimed = (
            self._db.table("ai_jobs")
            .update(
                {
                    "status": "running",
                    "progress_detail": "Claimed",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", job["id"])
            .eq("status", "queued")
            .execute()
        )
        if not claimed.data:
            return None
        return await self.process_job(claimed.data[0])
