"""Knowledge document ingestion and deterministic local retrieval."""

import hashlib
import math
import re
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import KnowledgeSource
from app.config import Settings
from app.models import KnowledgeChunk, utc_now

TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
CHUNK_WORDS = 180
OVERLAP_WORDS = 30
VECTOR_DIMENSIONS = 384


def _vector(text: str) -> list[float]:
    """Build a deterministic feature-hashed embedding for portable indexing."""
    terms = [term.casefold() for term in TOKEN_RE.findall(text)]
    result = [0.0] * VECTOR_DIMENSIONS
    for term in terms:
        if len(term) > 1:
            index = int.from_bytes(hashlib.blake2b(term.encode(), digest_size=4).digest(), "big") % VECTOR_DIMENSIONS
            result[index] += 1.0
    return result


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(value * value for value in left))
    norm_right = math.sqrt(sum(value * value for value in right))
    return dot / (norm_left * norm_right) if norm_left and norm_right else 0.0


def _chunks(text: str) -> list[str]:
    words = text.split()
    step = CHUNK_WORDS - OVERLAP_WORDS
    return [" ".join(words[start : start + CHUNK_WORDS]) for start in range(0, len(words), step)]


class KnowledgeBase:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def ingest(self) -> int:
        """Rebuild indexed chunks from Markdown/text and PDF files."""
        root = Path(self.settings.knowledge_base_path)
        documents: list[tuple[str, str, str]] = []
        if root.exists():
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".pdf"}:
                    continue
                if path.suffix.lower() == ".pdf":
                    try:
                        from pypdf import PdfReader
                    except ImportError as exc:
                        raise RuntimeError("Install pypdf to ingest PDF sources.") from exc
                    text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
                else:
                    text = path.read_text(encoding="utf-8")
                if text.strip():
                    source = path.relative_to(root).as_posix()
                    title = path.stem.replace("_", " ").replace("-", " ").title()
                    documents.append((source, title, text))
        await self.session.execute(delete(KnowledgeChunk))
        count = 0
        for source, title, text in documents:
            for index, content in enumerate(_chunks(text)):
                self.session.add(KnowledgeChunk(
                    source=source, title=title, chunk_index=index, content=content,
                    embedding=_vector(content), updated_at=utc_now(),
                ))
                count += 1
        await self.session.flush()
        return count

    async def retrieve(self, query: str, limit: int = 4) -> list[tuple[KnowledgeSource, float]]:
        rows = await self.session.scalars(select(KnowledgeChunk))
        query_vector = _vector(query)
        scored = []
        for row in rows:
            score = _cosine(query_vector, row.embedding)
            if score >= self.settings.rag_min_score:
                scored.append((row, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return [
            (KnowledgeSource(
                title=row.title, source=row.source,
                excerpt=row.content[:500] + ("…" if len(row.content) > 500 else ""),
            ), score)
            for row, score in scored[:limit]
        ]
