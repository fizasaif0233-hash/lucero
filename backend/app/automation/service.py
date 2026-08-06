"""Orchestrates plan → draft → approve → execute for all automation modules."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.ai.service import AIService
from app.automation.base import AutomationModule, RunStatus
from app.automation.modules import build_modules
from app.automation.repository import AutomationRepository
from app.rag.retriever import Retriever
from app.utils.logging import get_logger

logger = get_logger(__name__)


MODULE_CATALOG = [
    {
        "id": "email",
        "title": "Email Automation",
        "description": "Draft personalized distributor/CRM emails. Review before send.",
        "example": "Email all distributors.",
        "status": "ready",
    },
    {
        "id": "calendar",
        "title": "Calendar & Booking",
        "description": "Prepare tastings and meetings. Confirm before saving.",
        "example": "Schedule a tequila tasting next Friday at 6 PM.",
        "status": "ready",
    },
    {
        "id": "marketing",
        "title": "Marketing Automation",
        "description": "Generate weekly multi-channel content into Marketing Library.",
        "example": "Generate this week's marketing content.",
        "status": "ready",
    },
    {
        "id": "research",
        "title": "Research Automation",
        "description": "Executive research with companies, recommendations, next steps.",
        "example": "Research premium tequila distributors.",
        "status": "ready",
    },
    {
        "id": "report",
        "title": "Report Generation",
        "description": "Business performance, pipeline, risks, and recommendations.",
        "example": "Generate this week's executive report.",
        "status": "ready",
    },
    {
        "id": "support",
        "title": "Customer Support",
        "description": "Draft customer replies for approval before sending.",
        "example": "Create replies for today's customer messages.",
        "status": "ready",
    },
    {
        "id": "crm",
        "title": "CRM Management",
        "description": "Organize contacts into High / Medium / Low with follow-ups.",
        "example": "Prioritize my CRM contacts and recommend follow-ups.",
        "status": "ready",
    },
]


class AutomationService:
    def __init__(
        self,
        ai_service: AIService,
        retriever: Retriever,
        repo: Optional[AutomationRepository] = None,
    ) -> None:
        self._ai = ai_service
        self._retriever = retriever
        self._repo = repo or AutomationRepository()
        self._modules = build_modules(ai_service)

    def catalog(self) -> List[Dict[str, Any]]:
        return MODULE_CATALOG

    async def start_run(
        self,
        *,
        user_id: str | UUID,
        module: str,
        prompt: str,
    ) -> dict:
        mod_key = AutomationModule(module)
        handler = self._modules[mod_key]
        run = self._repo.create_run(
            user_id=user_id,
            module=module,
            title=handler.label,
            prompt=prompt,
            status=RunStatus.PLANNING.value,
        )

        try:
            knowledge = await self._knowledge_for(module, prompt, user_id)
            bundle = await handler.plan_and_draft(
                user_id=user_id, prompt=prompt, knowledge=knowledge
            )
            items_payload = [
                {
                    "item_type": i.item_type,
                    "title": i.title,
                    "content": i.content,
                    "sort_order": i.sort_order,
                    "status": "draft",
                }
                for i in bundle.items
            ]
            saved_items = self._repo.replace_items(
                run_id=run["id"], user_id=user_id, items=items_payload
            )
            updated = self._repo.update_run(
                run["id"],
                title=bundle.title,
                status=RunStatus.AWAITING_APPROVAL.value,
                plan_summary=bundle.plan_summary,
                preview=bundle.preview,
            )
            return self._serialize_run(updated, saved_items)
        except Exception as exc:
            logger.exception("automation_draft_failed", module=module)
            failed = self._repo.update_run(
                run["id"],
                status=RunStatus.FAILED.value,
                error_message=str(exc),
            )
            return self._serialize_run(failed, [])

    async def approve_run(
        self, *, user_id: str | UUID, run_id: str | UUID
    ) -> dict:
        run = self._repo.get_run(run_id, user_id)
        if not run:
            raise ValueError("Automation run not found")
        if run["status"] not in {
            RunStatus.AWAITING_APPROVAL.value,
            RunStatus.DRAFT_READY.value,
        }:
            raise ValueError(f"Run cannot be approved from status {run['status']}")

        items = self._repo.list_items(run_id)
        handler = self._modules[AutomationModule(run["module"])]
        self._repo.update_run(run_id, status=RunStatus.APPROVED.value)

        try:
            result = await handler.execute(
                user_id=user_id,
                run_id=run_id,
                items=items,
                preview=run.get("preview") or {},
            )
            for item in items:
                self._repo.update_item(
                    item["id"], user_id, status="executed"
                )
            updated = self._repo.update_run(
                run_id,
                status=RunStatus.EXECUTED.value,
                result={
                    "summary": result.summary,
                    "details": result.details,
                },
            )
            return self._serialize_run(updated, self._repo.list_items(run_id))
        except Exception as exc:
            logger.exception("automation_execute_failed", run_id=str(run_id))
            failed = self._repo.update_run(
                run_id,
                status=RunStatus.FAILED.value,
                error_message=str(exc),
            )
            return self._serialize_run(failed, items)

    def cancel_run(self, *, user_id: str | UUID, run_id: str | UUID) -> dict:
        run = self._repo.get_run(run_id, user_id)
        if not run:
            raise ValueError("Automation run not found")
        updated = self._repo.update_run(
            run_id, status=RunStatus.CANCELLED.value
        )
        return self._serialize_run(updated, self._repo.list_items(run_id))

    def get_run(self, *, user_id: str | UUID, run_id: str | UUID) -> Optional[dict]:
        run = self._repo.get_run(run_id, user_id)
        if not run:
            return None
        return self._serialize_run(run, self._repo.list_items(run_id))

    def history(
        self, *, user_id: str | UUID, module: Optional[str] = None
    ) -> List[dict]:
        runs = self._repo.list_runs(user_id, module=module)
        return [
            {
                "id": r["id"],
                "module": r["module"],
                "title": r["title"],
                "prompt": r["prompt"],
                "status": r["status"],
                "plan_summary": r.get("plan_summary"),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in runs
        ]

    def update_item(
        self,
        *,
        user_id: str | UUID,
        item_id: str | UUID,
        content: Dict[str, Any],
        title: Optional[str] = None,
    ) -> dict:
        fields: Dict[str, Any] = {"content": content, "status": "edited"}
        if title:
            fields["title"] = title
        return self._repo.update_item(item_id, user_id, **fields)

    async def _knowledge_for(
        self, module: str, prompt: str, user_id: str | UUID
    ) -> str:
        queries = [prompt]
        if module == "email":
            queries.append("distributor CRM contacts Foley African Eastern")
        elif module == "research":
            queries.append("premium tequila distributors Global Target Research")
        elif module in {"marketing", "report"}:
            queries.append("759 Blue Prince21 brand pitch marketing playbook")
        elif module == "support":
            queries.append("759 Tequila FAQ tasting shipping payment")
        chunks = []
        seen = set()
        for q in queries:
            hits = await self._retriever.retrieve(q, user_id, top_k=6, threshold=0.28)
            for h in hits:
                if h.id in seen:
                    continue
                seen.add(h.id)
                chunks.append(h.content)
        return "\n\n---\n\n".join(chunks[:10])

    @staticmethod
    def _serialize_run(run: dict, items: List[dict]) -> dict:
        return {
            "id": run.get("id"),
            "module": run.get("module"),
            "title": run.get("title"),
            "prompt": run.get("prompt"),
            "status": run.get("status"),
            "plan_summary": run.get("plan_summary"),
            "preview": run.get("preview") or {},
            "result": run.get("result") or {},
            "error_message": run.get("error_message"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "items": items,
        }
