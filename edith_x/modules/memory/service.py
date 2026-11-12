"""M13 — Memory: Per-user/team/org persistent memory via mem0 + Qdrant fallback."""
from __future__ import annotations

import time
import uuid
import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import MemoryItem
from edith_x.modules.knowledge.service import _hash_vector

log = structlog.get_logger(__name__)


class MemoryService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._mem0 = None
        self._initialized = False
        # Resilient local fallback store: user_id -> list of memories
        self._fallback_store: dict[str, list[dict]] = {}

    async def _ensure_init(self) -> None:
        if self._initialized:
            return
        try:
            from mem0 import Memory
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "host": self._settings.qdrant_host,
                        "port": self._settings.qdrant_port,
                    },
                },
                "llm": {
                    "provider": "openai",
                    "config": {"api_key": self._settings.openai_api_key or "placeholder"},
                },
                "embedder": {
                    "provider": "huggingface",
                    "config": {"model": self._settings.embedding_model},
                },
            }
            self._mem0 = Memory.from_config(config)
            log.info("memory_service_initialized")
        except Exception as e:
            log.info("mem0_not_configured_using_resilient_store", reason=str(e))
        self._initialized = True

    async def get(self, user_id: str, query: str, top_k: int = 5) -> list[MemoryItem]:
        await self._ensure_init()
        if self._mem0:
            try:
                results = self._mem0.search(query=query, user_id=user_id, limit=top_k)
                return [
                    MemoryItem(
                        id=r.get("id", ""),
                        content=r.get("memory", ""),
                        scope="user",
                        relevance=r.get("score", 0.0),
                    )
                    for r in (results.get("results") or [])
                ]
            except Exception as e:
                log.warning("memory_get_remote_failed_using_fallback", error=str(e))

        # Local resilient fallback retrieval
        user_memories = self._fallback_store.get(user_id, [])
        if not user_memories:
            return []

        q_terms = set(query.lower().split())
        scored: list[tuple[float, dict]] = []
        for m in user_memories:
            content_lower = m["content"].lower()
            overlap = sum(1 for t in q_terms if t in content_lower)
            score = overlap / max(len(q_terms), 1)
            scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            MemoryItem(
                id=m["id"],
                content=m["content"],
                scope=m.get("scope", "user"),
                relevance=score,
                metadata=m.get("metadata", {}),
            )
            for score, m in scored[:top_k]
        ]

    async def store(self, user_id: str, content: str, scope: str = "user") -> None:
        await self._ensure_init()
        if self._mem0:
            try:
                self._mem0.add(content, user_id=user_id)
                log.info("memory_stored_mem0", user_id=user_id, scope=scope)
                return
            except Exception as e:
                log.warning("memory_store_mem0_failed", error=str(e))

        # Store in fallback
        if user_id not in self._fallback_store:
            self._fallback_store[user_id] = []
        mem_id = f"mem_{uuid.uuid4().hex[:8]}"
        self._fallback_store[user_id].append({
            "id": mem_id,
            "content": content,
            "scope": scope,
            "timestamp": time.time(),
        })
        log.info("memory_stored_fallback", user_id=user_id, id=mem_id)

    async def forget(self, user_id: str, memory_id: str) -> None:
        await self._ensure_init()
        if self._mem0:
            try:
                self._mem0.delete(memory_id=memory_id)
            except Exception as e:
                log.warning("memory_forget_failed", error=str(e))

        if user_id in self._fallback_store:
            self._fallback_store[user_id] = [
                m for m in self._fallback_store[user_id] if m["id"] != memory_id
            ]
