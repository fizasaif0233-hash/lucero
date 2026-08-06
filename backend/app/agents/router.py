"""Task routing for L.U.C.E.R.O business-partner workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class TaskIntent(str, Enum):
    CHAT = "chat"
    KNOWLEDGE = "knowledge"
    RESEARCH = "research"
    MARKETING = "marketing"
    PERSONAL = "personal"


@dataclass(frozen=True)
class RoutedTask:
    intent: TaskIntent
    reason: str
    search_queries: tuple[str, ...] = ()


class TaskRouter:
    """
    Lightweight intent router.

    Phase 1: knowledge + chat + marketing writing from RAG/AI
    Phase 2+: research/marketing/automation agents plug in here
    """

    RESEARCH_PATTERNS = (
        r"\bfind\b.+\b(investor|investors|distributor|distributors|restaurant|restaurants|celebrity|celebrities|influencer|influencers|lead|leads|contact|contacts)\b",
        r"\bresearch\b",
        r"\bsearch (the )?(web|internet|online)\b",
        r"\blook up\b",
        r"\bwho (is|are) (looking to invest|investing)\b",
        r"\binvestors? interested\b",
        r"\bgo (out and )?research\b",
        r"\bdiscover\b.+\b(investor|distributor|partner)",
    )

    KNOWLEDGE_PATTERNS = (
        r"\b(my|our)\b.+\b(business|brand|tequila|token|exchange|roadmap|pricing|product|products|competitor|competitors|customer|customers)\b",
        r"\btell me about\b",
        r"\bexplain\b.+\b(token|exchange|model|onboarding|financial|pitch)\b",
        r"\bwhat (is|are)\b.+\b(759|tequila|token|exchange|blue prince)\b",
        r"\bsummarize\b.+\b(document|pitch|plan|model|business)\b",
        r"\bwho are my\b",
        r"\bdubai distributor",
        r"\bfinancial model\b",
        r"\bprojected revenue\b",
        r"\bmonthly cost\b",
        r"\bcapital (do i|needed)\b",
        r"\bonboarding\b",
        r"\bbrand story\b",
        r"\btarget customer\b",
        r"\bfrom (my|our) (documents|files|assets|crm)\b",
        r"\bsearch my documents\b",
        r"\bfind my\b",
    )

    MARKETING_PATTERNS = (
        r"\b(create|write|draft|generate)\b.+\b(post|caption|email|ad|advertisement|campaign|script)\b",
        r"\bfacebook\b",
        r"\binstagram\b",
        r"\bmarketing ideas?\b",
        r"\bsocial media\b",
    )

    PERSONAL_PATTERNS = (
        r"\b(tasks? today|remind me|summarize yesterday|what should i (work on|do) today)\b",
        r"\bpriorit(y|ies)\b",
        r"\bto[- ]?do\b",
    )

    def route(self, message: str) -> RoutedTask:
        text = (message or "").strip()
        lower = text.lower()

        if self._matches(lower, self.RESEARCH_PATTERNS):
            queries = self._research_queries(text)
            return RoutedTask(
                intent=TaskIntent.RESEARCH,
                reason="External/research-style request",
                search_queries=queries,
            )

        if self._matches(lower, self.MARKETING_PATTERNS):
            return RoutedTask(
                intent=TaskIntent.MARKETING,
                reason="Marketing/content generation request",
                search_queries=(text,),
            )

        if self._matches(lower, self.PERSONAL_PATTERNS):
            return RoutedTask(
                intent=TaskIntent.PERSONAL,
                reason="Personal assistant / prioritization request",
                search_queries=(
                    "weekly playbook tasks priorities distributor outreach influencer",
                    text,
                ),
            )

        if self._matches(lower, self.KNOWLEDGE_PATTERNS):
            return RoutedTask(
                intent=TaskIntent.KNOWLEDGE,
                reason="Internal business knowledge request",
                search_queries=self._knowledge_queries(text),
            )

        # Default: treat as knowledge-aware chat
        return RoutedTask(
            intent=TaskIntent.CHAT,
            reason="General conversation",
            search_queries=(text,),
        )

    @staticmethod
    def _matches(text: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

    @staticmethod
    def _research_queries(text: str) -> tuple[str, ...]:
        lower = text.lower()
        queries = [text]
        if "investor" in lower or "invest" in lower:
            queries.extend(
                [
                    "tequila crypto investors BlockBar NFT spirits collectors",
                    "CRYPTO WHALES NFT COLLECTORS luxury spirits investment",
                    "luxury beverage venture capital investors",
                    "crypto whale luxury spirits investment targets Blue Prince21",
                    "celebrity tequila brand investors partners Global Target Research",
                    "PRIVATE MEMBERS CLUBS Soho House crypto luxury buyer segments",
                ]
            )
        if "distributor" in lower:
            queries.extend(
                [
                    "priority distributor research Dubai Tokyo London",
                    "tequila distributor importer targets Foley Family",
                ]
            )
        if "celebrity" in lower or "influencer" in lower:
            queries.append("celebrity influencer partner research tequila")
        if "restaurant" in lower:
            queries.append("luxury restaurant bar hospitality tequila targets")
        # dedupe preserve order
        seen = set()
        out = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                out.append(q)
        return tuple(out[:6])

    @staticmethod
    def _knowledge_queries(text: str) -> tuple[str, ...]:
        lower = text.lower()
        queries = [text]
        if "dubai" in lower:
            queries.append("Dubai UAE distributor African Eastern Duty Free")
        if "token" in lower or "exchange" in lower:
            queries.append("759 Private Exchange token member onboarding tiers")
        if "financial" in lower or "revenue" in lower or "cost" in lower:
            queries.append("759 financial model projected revenue capital")
        if "business" in lower:
            queries.append(
                "Blue Prince21 McKinzy 759 Tequila token ecosystem brand overview"
            )
        if "onboarding" in lower:
            queries.append("759 Token Member Onboarding Flow")
        seen = set()
        out = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                out.append(q)
        return tuple(out[:5])
