"""Automation module contracts and shared types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID


class AutomationModule(str, Enum):
    EMAIL = "email"
    CALENDAR = "calendar"
    MARKETING = "marketing"
    RESEARCH = "research"
    REPORT = "report"
    SUPPORT = "support"
    CRM = "crm"


class RunStatus(str, Enum):
    PLANNING = "planning"
    DRAFT_READY = "draft_ready"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class DraftItem:
    item_type: str
    title: str
    content: Dict[str, Any]
    sort_order: int = 0


@dataclass
class DraftBundle:
    title: str
    plan_summary: str
    items: List[DraftItem] = field(default_factory=list)
    preview: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecuteResult:
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)


class AutomationModuleBase(ABC):
    module: AutomationModule
    label: str
    description: str

    @abstractmethod
    async def plan_and_draft(
        self,
        *,
        user_id: str | UUID,
        prompt: str,
        knowledge: str = "",
    ) -> DraftBundle:
        raise NotImplementedError

    @abstractmethod
    async def execute(
        self,
        *,
        user_id: str | UUID,
        run_id: str | UUID,
        items: List[dict],
        preview: Dict[str, Any],
    ) -> ExecuteResult:
        raise NotImplementedError
