from dataclasses import dataclass, replace
import re
from typing import Dict, List, Optional, Set
from uuid import UUID

from app.ai.service import AIService
from app.core.config import Settings, get_settings
from app.database.client import get_supabase_admin
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    id: str
    document_id: str
    content: str
    similarity: float
    metadata: dict

    @property
    def document_name(self) -> str:
        return (
            self.metadata.get("document_name")
            or self.metadata.get("original_filename")
            or self.metadata.get("filename")
            or "Unknown document"
        )

    @property
    def section(self) -> str:
        return self.metadata.get("section") or "General"

    @property
    def chunk_index(self) -> int | str:
        return self.metadata.get("chunk_index", "?")


class Retriever:
    """Embed a query and fetch similar document chunks via pgvector + keyword fallback."""

    def __init__(
        self,
        ai_service: AIService,
        settings: Optional[Settings] = None,
    ) -> None:
        self._ai = ai_service
        self._settings = settings or get_settings()
        self._db = get_supabase_admin()

    async def retrieve(
        self,
        query: str,
        user_id: str | UUID,
        *,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        top_k = top_k or self._settings.rag_top_k
        threshold = (
            threshold
            if threshold is not None
            else self._settings.rag_similarity_threshold
        )

        chunks = await self._vector_search(
            query, user_id, top_k=top_k, threshold=threshold
        )

        # Phrase / keyword fallback (important for "which document contains X")
        phrase_hits = self._phrase_search(query, user_id, top_k=top_k)
        if phrase_hits:
            chunks = self._merge(phrase_hits, chunks, top_k=top_k)
        elif len(chunks) < max(3, top_k // 2):
            keyword_hits = self._keyword_search(query, user_id, top_k=top_k)
            chunks = self._merge(chunks, keyword_hits, top_k=top_k)

        chunks = self._enrich_sources(chunks)

        logger.info(
            "rag_retrieve",
            user_id=str(user_id),
            hits=len(chunks),
            top_k=top_k,
            threshold=threshold,
        )
        return chunks

    async def _vector_search(
        self,
        query: str,
        user_id: str | UUID,
        *,
        top_k: int,
        threshold: float,
    ) -> List[RetrievedChunk]:
        vectors = await self._ai.embed_texts([query])
        if not vectors:
            return []

        try:
            result = self._db.rpc(
                "match_document_chunks",
                {
                    "query_embedding": vectors[0],
                    "match_user_id": str(user_id),
                    "match_count": top_k,
                    "match_threshold": threshold,
                },
            ).execute()
        except Exception as exc:
            logger.warning("rag_vector_failed", error=str(exc))
            return []

        chunks: List[RetrievedChunk] = []
        for row in result.data or []:
            chunks.append(
                RetrievedChunk(
                    id=row["id"],
                    document_id=row["document_id"],
                    content=row["content"],
                    similarity=float(row.get("similarity") or 0),
                    metadata=row.get("metadata") or {},
                )
            )
        return chunks

    def _phrase_search(
        self,
        query: str,
        user_id: str | UUID,
        *,
        top_k: int,
    ) -> List[RetrievedChunk]:
        """Exact / near-exact phrase match for citation questions."""
        quoted = re.findall(r'"([^"]{3,120})"', query)
        # Also treat distinctive multi-word phrases without quotes
        candidates = list(quoted)
        cleaned = re.sub(
            r"\b(which|document|contains|phrase|the|find|where|show|source)\b",
            " ",
            query,
            flags=re.I,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ?!.\"'")
        if len(cleaned) >= 8:
            candidates.append(cleaned)

        found: List[RetrievedChunk] = []
        seen: Set[str] = set()
        for phrase in candidates[:3]:
            try:
                result = (
                    self._db.table("document_chunks")
                    .select("id, document_id, content, metadata, user_id, is_shared")
                    .ilike("content", f"%{phrase}%")
                    .limit(top_k)
                    .execute()
                )
            except Exception as exc:
                logger.warning("rag_phrase_failed", phrase=phrase, error=str(exc))
                continue

            for row in result.data or []:
                if row.get("user_id") != str(user_id) and not row.get("is_shared"):
                    continue
                chunk_id = row["id"]
                if chunk_id in seen:
                    continue
                seen.add(chunk_id)
                found.append(
                    RetrievedChunk(
                        id=chunk_id,
                        document_id=row["document_id"],
                        content=row["content"],
                        similarity=0.92,
                        metadata={
                            **(row.get("metadata") or {}),
                            "match": "phrase",
                            "matched_phrase": phrase,
                        },
                    )
                )
                if len(found) >= top_k:
                    return found
        return found

    def _keyword_search(
        self,
        query: str,
        user_id: str | UUID,
        *,
        top_k: int,
    ) -> List[RetrievedChunk]:
        terms = self._query_terms(query)
        if not terms:
            return []

        found: List[RetrievedChunk] = []
        seen: Set[str] = set()
        for term in terms[:6]:
            try:
                result = (
                    self._db.table("document_chunks")
                    .select("id, document_id, content, metadata, user_id, is_shared")
                    .ilike("content", f"%{term}%")
                    .limit(top_k)
                    .execute()
                )
            except Exception as exc:
                logger.warning("rag_keyword_failed", term=term, error=str(exc))
                continue

            for row in result.data or []:
                if row.get("user_id") != str(user_id) and not row.get("is_shared"):
                    continue
                chunk_id = row["id"]
                if chunk_id in seen:
                    continue
                seen.add(chunk_id)
                found.append(
                    RetrievedChunk(
                        id=chunk_id,
                        document_id=row["document_id"],
                        content=row["content"],
                        similarity=0.5,
                        metadata={
                            **(row.get("metadata") or {}),
                            "match": "keyword",
                            "term": term,
                        },
                    )
                )
                if len(found) >= top_k:
                    return found
        return found

    def _enrich_sources(self, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        if not chunks:
            return chunks

        doc_ids = list({c.document_id for c in chunks if c.document_id})
        docs_by_id: Dict[str, dict] = {}
        if doc_ids:
            try:
                result = (
                    self._db.table("business_documents")
                    .select(
                        "id, original_filename, filename, source_url, source_type"
                    )
                    .in_("id", doc_ids)
                    .execute()
                )
                docs_by_id = {row["id"]: row for row in (result.data or [])}
            except Exception as exc:
                logger.warning("rag_enrich_docs_failed", error=str(exc))

        enriched: List[RetrievedChunk] = []
        for chunk in chunks:
            doc = docs_by_id.get(chunk.document_id) or {}
            name = (
                chunk.metadata.get("document_name")
                or chunk.metadata.get("original_filename")
                or chunk.metadata.get("filename")
                or doc.get("original_filename")
                or doc.get("filename")
                or "Unknown document"
            )
            section = chunk.metadata.get("section") or self.infer_section(
                chunk.content
            )
            meta = {
                **chunk.metadata,
                "document_name": name,
                "original_filename": name,
                "section": section,
                "source_url": chunk.metadata.get("source_url")
                or doc.get("source_url"),
                "source_type": chunk.metadata.get("source_type")
                or doc.get("source_type")
                or "upload",
            }
            enriched.append(
                replace(chunk, metadata=meta)
            )
        return enriched

    @staticmethod
    def infer_section(content: str) -> str:
        """Infer a human section/heading from chunk text (not the document filename)."""
        lines = [ln.strip() for ln in (content or "").splitlines() if ln.strip()]
        for line in lines[:10]:
            if line.startswith("#"):
                return re.sub(r"^#+\s*", "", line).strip() or "General"
            # ALL CAPS headings like MOON LANDING
            letters = re.sub(r"[^A-Za-z]", "", line)
            if (
                len(line) <= 80
                and len(letters) >= 4
                and letters.isupper()
                and not line.endswith(":")
            ):
                return line
            # Title-like "Section Name" / "Landing Date" used as headings
            if re.match(r"^[A-Z][A-Za-z0-9 /&\-]{2,70}$", line) and len(line.split()) <= 8:
                # Prefer earlier heading-like lines; skip long prose sentences
                if "." not in line:
                    return line
        return "General"

    @staticmethod
    def _query_terms(query: str) -> List[str]:
        stop = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "to",
            "of",
            "in",
            "on",
            "for",
            "my",
            "our",
            "me",
            "i",
            "is",
            "are",
            "what",
            "who",
            "how",
            "find",
            "tell",
            "about",
            "please",
            "jarvis",
            "lucero",
            "hey",
            "which",
            "document",
            "contains",
            "phrase",
            "where",
            "did",
            "you",
            "get",
            "that",
            "information",
            "show",
            "source",
            "section",
        }
        raw = re.findall(r"[A-Za-z0-9][A-Za-z0-9+\-]{2,}", query.lower())
        terms = [t for t in raw if t not in stop]
        priority = [
            t
            for t in terms
            if t
            in {
                "dubai",
                "tokyo",
                "london",
                "distributor",
                "distributors",
                "investor",
                "investors",
                "tequila",
                "crypto",
                "token",
                "759",
                "exchange",
                "influencer",
                "celebrity",
                "pitch",
                "foley",
                "african",
                "tranquility",
                "apollo",
                "armstrong",
            }
        ]
        rest = [t for t in terms if t not in priority]
        return priority + rest

    @staticmethod
    def _merge(
        primary: List[RetrievedChunk],
        secondary: List[RetrievedChunk],
        *,
        top_k: int,
    ) -> List[RetrievedChunk]:
        seen: Set[str] = {c.id for c in primary}
        merged = list(primary)
        for chunk in secondary:
            if chunk.id in seen:
                continue
            merged.append(chunk)
            seen.add(chunk.id)
            if len(merged) >= top_k:
                break
        return merged

    @staticmethod
    def format_context(chunks: List[RetrievedChunk]) -> str:
        """Format retrieved chunks with explicit citation metadata for the LLM."""
        if not chunks:
            return ""
        parts = [
            "Retrieved sources (cite these exactly — Document Name is the file, "
            "Section is a heading inside the file, never swap them):",
            "",
        ]
        for i, chunk in enumerate(chunks, start=1):
            conf = (
                "High"
                if chunk.similarity >= 0.7
                else "Medium"
                if chunk.similarity >= 0.45
                else "Low"
            )
            matched = chunk.metadata.get("matched_phrase")
            header = [
                f"[Source {i}]",
                f"Document Name: {chunk.document_name}",
                f"Section: {chunk.section}",
                f"Chunk ID: {chunk.id}",
                f"Chunk Index: {chunk.chunk_index}",
                f"Similarity: {chunk.similarity:.2f}",
                f"Confidence: {conf}",
            ]
            if matched:
                header.append(f"Matched Phrase: {matched}")
            header.append("Content:")
            header.append(chunk.content.strip())
            parts.append("\n".join(header))
            parts.append("---")
        return "\n".join(parts)
