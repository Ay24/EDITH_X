"""M13 — Memory: Per-user/team/org persistent memory via mem0 + Qdrant."""
from __future__ import annotations

import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import MemoryItem

log = structlog.get_logger(__name__)


class MemoryService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._mem0 = None
        self._initialized = False

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
            log.warning("memory_init_failed", error=str(e))
        self._initialized = True

    async def get(self, user_id: str, query: str, top_k: int = 5) -> list[MemoryItem]:
        await self._ensure_init()
        if not self._mem0:
            return []
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
            log.warning("memory_get_failed", error=str(e))
            return []

    async def store(self, user_id: str, content: str, scope: str = "user") -> None:
        await self._ensure_init()
        if not self._mem0:
            return
        try:
            self._mem0.add(content, user_id=user_id)
            log.info("memory_stored", user_id=user_id, scope=scope)
        except Exception as e:
            log.warning("memory_store_failed", error=str(e))

    async def forget(self, user_id: str, memory_id: str) -> None:
        await self._ensure_init()
        if not self._mem0:
            return
        try:
            self._mem0.delete(memory_id=memory_id)
        except Exception as e:
            log.warning("memory_forget_failed", error=str(e))
