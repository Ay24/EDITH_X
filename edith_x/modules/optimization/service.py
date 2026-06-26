"""M8 — Optimization Engine: 4-layer cost firewall with semantic cache."""
from __future__ import annotations

import hashlib
import time
from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from edith_x.core.config import Settings
from edith_x.core.interfaces import CacheResult, CompressedPrompt

log = structlog.get_logger(__name__)

COLLECTION = "edith_semantic_cache"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2


class OptimizationService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._encoder: SentenceTransformer | None = None
        self._qdrant: AsyncQdrantClient | None = None
        self._initialized = False

    async def _ensure_init(self) -> None:
        if self._initialized:
            return
        # Try to load sentence-transformers (lazy to avoid PyTorch version issues)
        try:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(self._settings.embedding_model)
            log.info("embeddings_loaded", model=self._settings.embedding_model)
        except Exception as e:
            log.warning("embeddings_unavailable", error=str(e), fallback="hash_based")
            self._encoder = None

        try:
            self._qdrant = AsyncQdrantClient(
                host=self._settings.qdrant_host,
                port=self._settings.qdrant_port,
                api_key=self._settings.qdrant_api_key or None,
            )
            collections = await self._qdrant.get_collections()
            names = [c.name for c in collections.collections]
            if COLLECTION not in names:
                await self._qdrant.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
            log.info("qdrant_connected", host=self._settings.qdrant_host)
        except Exception as e:
            log.warning("qdrant_unavailable", error=str(e), fallback="in_memory_cache")
            self._qdrant = None

        self._initialized = True

    def _embed(self, text: str) -> list[float]:
        """Embed text — falls back to deterministic hash vector if encoder unavailable."""
        if self._encoder is not None:
            try:
                return self._encoder.encode(text).tolist()
            except Exception:
                pass
        # Deterministic hash-based pseudo-embedding fallback
        h = hashlib.sha256(text.encode()).digest()
        vec = [(b / 255.0) * 2 - 1 for b in h]  # 32 values in [-1, 1]
        # Pad/truncate to VECTOR_SIZE
        while len(vec) < VECTOR_SIZE:
            vec.extend(vec)
        return vec[:VECTOR_SIZE]

    async def check_cache(self, query: str) -> CacheResult | None:
        await self._ensure_init()
        if not self._qdrant or not self._encoder:
            return None
        try:
            embedding = self._embed(query)
            results = await self._qdrant.search(
                collection_name=COLLECTION,
                query_vector=embedding,
                limit=1,
                score_threshold=self._settings.cache_similarity_threshold,
            )
            if results:
                hit = results[0]
                response = hit.payload.get("response", "") if hit.payload else ""
                log.info("cache_hit", similarity=hit.score, query=query[:50])
                return CacheResult(
                    hit=True,
                    response=response,
                    similarity=hit.score,
                    saved_cost_usd=hit.payload.get("cost_usd", 0.003) if hit.payload else 0.003,
                )
        except Exception as e:
            log.warning("cache_check_failed", error=str(e))
        return CacheResult(hit=False)

    async def store_cache(self, query: str, response: str) -> None:
        await self._ensure_init()
        if not self._qdrant or not self._encoder:
            return
        try:
            embedding = self._embed(query)
            point_id = abs(hash(query)) % (2**63)
            await self._qdrant.upsert(
                collection_name=COLLECTION,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "query": query,
                            "response": response,
                            "timestamp": time.time(),
                            "cost_usd": 0.003,
                        },
                    )
                ],
            )
            log.info("cache_stored", query=query[:50])
        except Exception as e:
            log.warning("cache_store_failed", error=str(e))

    async def compress_prompt(self, prompt: str, budget: int) -> CompressedPrompt:
        """Phase 0: Simple truncation. Phase 1: DSPy compression."""
        original_tokens = await self.estimate_tokens(prompt)
        if original_tokens <= budget:
            return CompressedPrompt(
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compressed_text=prompt,
                compression_ratio=1.0,
            )
        # Simple sentence truncation for Phase 0
        sentences = prompt.split(". ")
        compressed = ""
        token_count = 0
        for sentence in sentences:
            est = len(sentence.split()) * 1.3
            if token_count + est > budget:
                break
            compressed += sentence + ". "
            token_count += est
        compressed = compressed.strip() or prompt[:budget * 4]
        compressed_tokens = await self.estimate_tokens(compressed)
        return CompressedPrompt(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compressed_text=compressed,
            compression_ratio=compressed_tokens / max(original_tokens, 1),
        )

    async def estimate_tokens(self, text: str) -> int:
        """Fast token estimation: ~1.3 tokens per word."""
        return int(len(text.split()) * 1.3)
