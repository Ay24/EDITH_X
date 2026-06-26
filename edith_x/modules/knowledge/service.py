"""M6 — Knowledge Layer: Hybrid retrieval stub for Phase 0."""
from __future__ import annotations
import structlog
from edith_x.core.config import Settings
from edith_x.core.interfaces import Document, KnowledgeChunk

log = structlog.get_logger(__name__)


class KnowledgeService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # In-memory doc store for Phase 0
        self._docs: list[dict] = []

    async def retrieve(self, query: str, sources: list[str], top_k: int = 10) -> list[KnowledgeChunk]:
        """Phase 0: Simple keyword match. Phase 2: Qdrant hybrid search."""
        results = []
        query_lower = query.lower()
        for doc in self._docs:
            if any(word in doc["content"].lower() for word in query_lower.split()):
                results.append(KnowledgeChunk(
                    content=doc["content"][:500],
                    source=doc["source"],
                    score=0.75,
                ))
                if len(results) >= top_k:
                    break
        log.info("knowledge_retrieved", chunks=len(results), query=query[:50])
        return results

    async def index(self, document: Document, source: str) -> str:
        self._docs.append({"content": document.content, "source": source, "id": document.id})
        log.info("document_indexed", source=source, id=document.id)
        return document.id
