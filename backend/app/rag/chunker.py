from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import Settings, get_settings


class DocumentChunker:
    """Split documents into overlapping chunks for embedding."""

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=cfg.rag_chunk_size,
            chunk_overlap=cfg.rag_chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, text: str) -> List[str]:
        chunks = self._splitter.split_text(text)
        return [c.strip() for c in chunks if c and c.strip()]
