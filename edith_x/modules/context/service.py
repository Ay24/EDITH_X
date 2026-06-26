"""M7 — Context Builder: Merges knowledge, history, and query into token-budgeted context."""
from __future__ import annotations
import structlog
from edith_x.core.config import Settings
from edith_x.core.interfaces import Context, KnowledgeChunk

log = structlog.get_logger(__name__)


class ContextBuilderService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def build(
        self,
        query: str,
        chunks: list[KnowledgeChunk],
        history: list[dict[str, str]],
        token_budget: int = 8000,
    ) -> Context:
        # Sort chunks by relevance score
        sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)

        # Deduplicate by content similarity (simple: exact substring check)
        deduped: list[KnowledgeChunk] = []
        seen_contents: set[str] = set()
        for chunk in sorted_chunks:
            key = chunk.content[:100]
            if key not in seen_contents:
                deduped.append(chunk)
                seen_contents.add(key)

        # Estimate tokens and fit within budget
        approx_tokens = sum(len(c.content.split()) * 1.3 for c in deduped)
        approx_tokens += sum(len(m.get("content", "").split()) * 1.3 for m in history)
        approx_tokens += len(query.split()) * 1.3

        # Trim chunks if over budget
        while approx_tokens > token_budget and deduped:
            removed = deduped.pop()
            approx_tokens -= len(removed.content.split()) * 1.3

        log.info("context_built", chunks=len(deduped), tokens=int(approx_tokens))
        return Context(
            query=query,
            chunks=deduped,
            history=history,
            token_count=int(approx_tokens),
            token_budget=token_budget,
        )
