"""Financial Analyst Agent — models, KPIs, forecasts."""

from __future__ import annotations

import re
from typing import List

from app.agents.specialist_base import AgentInfo, SpecialistAgent


class FinanceAgent(SpecialistAgent):
    info = AgentInfo(
        id="finance",
        name="Financial Analyst",
        title="Financial Analyst",
        description="Review financial models, revenue, costs, KPIs, and executive money recommendations.",
        skills=(
            "Financial model review",
            "Revenue & cost analysis",
            "Growth forecasts",
            "KPI calculation",
            "Cost-saving ideas",
            "Executive financial reports",
        ),
        icon="chart",
    )

    _PATTERNS = (
        r"\bfinancial\b",
        r"\brevenue\b",
        r"\bprofit\b|\bmargin\b",
        r"\bcost(s)?\b",
        r"\bforecast\b",
        r"\bkpi\b",
        r"\bbudget\b",
        r"\bcapital (do i|needed|require)",
        r"\bexcel\b|\bspreadsheet\b",
        r"\bmonthly cost\b",
        r"\bprojected\b",
        r"\bcashflow\b|\bcash flow\b",
    )

    def relevance(self, message: str) -> float:
        lower = message.lower()
        if "financial model" in lower or "projected revenue" in lower:
            return 0.98
        hits = sum(1 for p in self._PATTERNS if re.search(p, lower))
        return min(0.95, 0.5 + 0.15 * hits) if hits else 0.05

    def knowledge_queries(self, message: str) -> List[str]:
        return [
            message,
            "759 financial model projected revenue capital costs",
            "Blue Prince21 tequila pricing unit economics",
            "token economics investment model",
        ]

    def role_instructions(self) -> str:
        return (
            "You are L.U.C.E.R.O Financial Analyst. Use numbers only when present in knowledge. "
            "Never invent revenue or cost figures. Provide executive recommendations, "
            "KPIs, risks, and clear assumptions when estimating."
        )
