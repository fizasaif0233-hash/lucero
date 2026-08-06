"""Intelligent multi-agent router for L.U.C.E.R.O specialists."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from app.agents.specialist_base import SpecialistAgent


@dataclass(frozen=True)
class AgentRoute:
    agent_ids: tuple[str, ...]
    reason: str
    scores: Dict[str, float]
    collaborative: bool = False


class AgentRouter:
    """
    Scores each registered specialist and selects one or more agents.

    New agents appear automatically once added to the registry — no router rewrite.
    """

    SELECT_THRESHOLD = 0.45
    COLLAB_GAP = 0.18  # second agent kept if within this of the top score

    def __init__(self, agents: Dict[str, SpecialistAgent]) -> None:
        self._agents = agents

    def route(
        self,
        message: str,
        *,
        forced_agent_id: Optional[str] = None,
    ) -> AgentRoute:
        if forced_agent_id and forced_agent_id in self._agents:
            return AgentRoute(
                agent_ids=(forced_agent_id,),
                reason=f"User opened {self._agents[forced_agent_id].info.name}",
                scores={forced_agent_id: 1.0},
                collaborative=False,
            )

        scores: Dict[str, float] = {}
        for agent_id, agent in self._agents.items():
            scores[agent_id] = float(agent.relevance(message or ""))

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if not ranked or ranked[0][1] < self.SELECT_THRESHOLD:
            # General Lucero turn — do NOT force Document Agent (that caused
            # false "not in uploaded documents" refusals for normal questions).
            return AgentRoute(
                agent_ids=(),
                reason="General L.U.C.E.R.O assistant (docs + knowledge + web)",
                scores=scores,
                collaborative=False,
            )

        top_id, top_score = ranked[0]
        selected: List[str] = [top_id]
        for agent_id, score in ranked[1:]:
            if score < self.SELECT_THRESHOLD:
                break
            if top_score - score <= self.COLLAB_GAP or self._explicit_multi(message):
                if agent_id not in selected:
                    selected.append(agent_id)
            if len(selected) >= 3:
                break

        # Explicit multi-intent phrases force collaboration
        if self._explicit_multi(message):
            for agent_id, score in ranked:
                if score >= 0.4 and agent_id not in selected:
                    selected.append(agent_id)
                if len(selected) >= 3:
                    break

        names = [self._agents[i].info.name for i in selected]
        return AgentRoute(
            agent_ids=tuple(selected),
            reason=(
                "Collaborative: " + " → ".join(names)
                if len(selected) > 1
                else f"Routed to {names[0]}"
            ),
            scores=scores,
            collaborative=len(selected) > 1,
        )

    @staticmethod
    def _explicit_multi(message: str) -> bool:
        lower = (message or "").lower()
        return any(
            phrase in lower
            for phrase in (
                " and create ",
                " and generate ",
                " and write ",
                " then create ",
                " then generate ",
                " as well as ",
                " and also ",
                "review my financial",
                "financial model and",
                "marketing strategy and",
            )
        )

    def describe(self, agent_ids: Sequence[str]) -> List[dict]:
        out = []
        for aid in agent_ids:
            agent = self._agents.get(aid)
            if not agent:
                continue
            out.append(
                {
                    "id": agent.info.id,
                    "name": agent.info.name,
                    "title": agent.info.title,
                }
            )
        return out
