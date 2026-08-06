from typing import List, Optional
from uuid import UUID

from app.database.client import get_supabase_admin
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AutomationRepository:
    def __init__(self) -> None:
        self._db = get_supabase_admin()

    def create_run(
        self,
        *,
        user_id: str | UUID,
        module: str,
        title: str,
        prompt: str,
        status: str = "planning",
    ) -> dict:
        result = (
            self._db.table("automation_runs")
            .insert(
                {
                    "user_id": str(user_id),
                    "module": module,
                    "title": title,
                    "prompt": prompt,
                    "status": status,
                }
            )
            .execute()
        )
        return result.data[0]

    def update_run(self, run_id: str | UUID, **fields) -> dict:
        result = (
            self._db.table("automation_runs")
            .update(fields)
            .eq("id", str(run_id))
            .execute()
        )
        return (result.data or [{}])[0]

    def get_run(self, run_id: str | UUID, user_id: str | UUID) -> Optional[dict]:
        result = (
            self._db.table("automation_runs")
            .select("*")
            .eq("id", str(run_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def list_runs(
        self,
        user_id: str | UUID,
        *,
        module: Optional[str] = None,
        limit: int = 40,
    ) -> List[dict]:
        q = (
            self._db.table("automation_runs")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
        )
        if module:
            q = q.eq("module", module)
        return q.execute().data or []

    def replace_items(
        self,
        *,
        run_id: str | UUID,
        user_id: str | UUID,
        items: List[dict],
    ) -> List[dict]:
        self._db.table("automation_items").delete().eq("run_id", str(run_id)).execute()
        if not items:
            return []
        payload = []
        for item in items:
            payload.append(
                {
                    "run_id": str(run_id),
                    "user_id": str(user_id),
                    "item_type": item["item_type"],
                    "title": item["title"],
                    "content": item["content"],
                    "status": item.get("status") or "draft",
                    "sort_order": item.get("sort_order") or 0,
                }
            )
        result = self._db.table("automation_items").insert(payload).execute()
        return result.data or []

    def list_items(self, run_id: str | UUID) -> List[dict]:
        result = (
            self._db.table("automation_items")
            .select("*")
            .eq("run_id", str(run_id))
            .order("sort_order")
            .execute()
        )
        return result.data or []

    def update_item(self, item_id: str | UUID, user_id: str | UUID, **fields) -> dict:
        result = (
            self._db.table("automation_items")
            .update(fields)
            .eq("id", str(item_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return (result.data or [{}])[0]
