"""Document Agent — RAG knowledge assistant with source citations."""

from __future__ import annotations

import re
from typing import List
from uuid import UUID

from app.agents.specialist_base import AgentContext, AgentInfo, SpecialistAgent
from app.rag.retriever import Retriever


class DocumentAgent(SpecialistAgent):
    info = AgentInfo(
        id="document",
        name="Document Agent",
        title="Document Agent",
        description="Search and summarize uploaded documents, Assets, and website knowledge.",
        skills=(
            "Search uploaded files",
            "Summarize PDF / DOCX / TXT / CSV",
            "Cite document name + section",
            "Extract action items",
            "Answer document questions",
            "RAG + vector search",
        ),
        icon="file",
    )

    _PATTERNS = (
        r"\bsummarize\b",
        r"\bdocument",
        r"\bpitch deck\b",
        r"\buploaded\b",
        r"\bpdf\b|\bdocx\b|\bcsv\b",
        r"\bsearch my (documents|files|assets)\b",
        r"\bfrom (my|the) (docs|documents|files)\b",
        r"\baction items?\b",
        r"\btoken documents?\b",
        r"\bwhat does (my|the) .+ say\b",
        r"\bexplain my (token|pitch|playbook)\b",
        r"\bwhere did you get\b",
        r"\bsource (document|section)\b",
        r"\bwhich document\b",
        r"\bcontains the phrase\b",
        r"\bcite\b|\bcitation\b",
        r"\bsea of tranquility\b",
    )

    def relevance(self, message: str) -> float:
        lower = message.lower()
        if any(
            p in lower
            for p in (
                "where did you get",
                "which document",
                "source document",
                "contains the phrase",
                "show the source",
            )
        ):
            return 0.99
        hits = sum(1 for p in self._PATTERNS if re.search(p, lower))
        if "summarize" in lower and (
            "document" in lower or "token" in lower or "pitch" in lower
        ):
            return 0.95
        if hits:
            return min(0.9, 0.55 + 0.12 * hits)
        if re.search(
            r"\b(what is|tell me about|explain)\b.+\b(759|token|exchange|tequila)\b",
            lower,
        ):
            return 0.55
        return 0.15

    def knowledge_queries(self, message: str) -> List[str]:
        queries = [message]
        # Pull quoted phrases for exact search
        for phrase in re.findall(r'"([^"]{3,120})"', message):
            queries.insert(0, f'"{phrase}"')
        # Unquoted distinctive phrases after "phrase"
        m = re.search(r"phrase\s+[\"']?([^\"'.?]+)[\"']?", message, re.I)
        if m:
            queries.insert(0, m.group(1).strip())
        queries.extend(
            [
                "759 Private Exchange token member onboarding",
                "Blue Prince21 McKinzy pitch deck summary",
                "759inc.blue product knowledge",
            ]
        )
        # dedupe
        seen = set()
        out = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                out.append(q)
        return out[:6]

    def role_instructions(self) -> str:
        return (
            "You are L.U.C.E.R.O Document Agent.\n"
            "Answer questions ONLY using retrieved document content below.\n"
            "Every answer MUST include:\n"
            "- Document Name (the file name from 'Document Name:' fields — never invent)\n"
            "- Section or Heading (from 'Section:' fields — never confuse Section with Document Name)\n"
            "- Confidence (High/Medium/Low from the source block)\n"
            "- A short matched excerpt when relevant\n\n"
            "Format citations like:\n"
            "Source:\n"
            "Document: <Document Name>\n"
            "Section: <Section>\n"
            "Matched Text:\n"
            "<excerpt>\n\n"
            "If the user asks where information came from, list the Document Name and Section "
            "from the retrieved sources that support your prior answer.\n"
            "If the answer is not present in the retrieved documents, respond exactly:\n"
            '"I could not find this information in the uploaded documents."\n'
            "Never claim you don't know the source if the information came from retrieved documents.\n"
            "Never treat a section heading as the document filename."
        )

    async def gather_context(
        self, *, user_id: str | UUID, message: str
    ) -> AgentContext:
        queries = self.knowledge_queries(message)
        hits_all = []
        seen = set()
        for q in queries[:5]:
            hits = await self._retriever.retrieve(
                q, user_id, top_k=8, threshold=0.25
            )
            for h in hits:
                if h.id in seen:
                    continue
                seen.add(h.id)
                hits_all.append(h)
            if len(hits_all) >= 10:
                break

        knowledge = Retriever.format_context(hits_all[:10])
        return AgentContext(
            agent_id=self.info.id,
            agent_name=self.info.name,
            knowledge=knowledge,
            instructions=self.role_instructions(),
            search_queries=queries,
            metadata={"rag_chunks": len(hits_all), "sources": [
                {
                    "document_name": h.document_name,
                    "section": h.section,
                    "similarity": h.similarity,
                    "chunk_id": h.id,
                }
                for h in hits_all[:10]
            ]},
        )
