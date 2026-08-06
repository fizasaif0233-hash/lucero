"""Agent contracts — Phase 2+ modules plug in here."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List


@dataclass
class AgentProgress:
    step: str
    detail: str = ""


@dataclass
class AgentResult:
    summary: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    context_block: str = ""


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, query: str, **kwargs) -> AsyncIterator[AgentProgress | AgentResult]:
        """Yield progress updates, then a final AgentResult."""
        raise NotImplementedError
