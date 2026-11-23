"""M8 — Optimization Engine: 4-layer cost firewall with real semantic cache and information-density compressor."""
from __future__ import annotations

import asyncio
import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import CacheResult, CompressedPrompt
from edith_x.modules.optimization.cache import SemanticCache
from edith_x.modules.optimization.compressor import InformationDensityCompressor

log = structlog.get_logger(__name__)


class OptimizationService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache = SemanticCache(
            similarity_threshold=0.90,
            max_entries=10000,
            default_ttl_seconds=86400.0,
        )
        self._compressor = InformationDensityCompressor()
        self._initialized = True
        log.info("optimization_service_initialized", cache="semantic_and_exact", compressor="information_density")

    @property
    def cache(self) -> SemanticCache:
        return self._cache

    def purge_user_data(self, user_id: str) -> int:
        """Purge all cache entries matching user_id or user tag."""
        return self._cache.invalidate_by_user(user_id)

    async def check_cache(
        self,
        query: str,
        org_id: str = "default",
        user_role: str = "default",
        user_id: str | None = None,
    ) -> CacheResult | None:
        """Check L0 dual exact and semantic cache with tenant and RBAC isolation."""
        result = await self._cache.get(
            query,
            org_id=org_id,
            user_role=user_role,
            user_id=user_id,
        )
        if result.hit:
            log.info(
                "cache_hit",
                similarity=result.similarity,
                saved_usd=result.saved_cost_usd,
                org_id=org_id,
                user_role=user_role,
                query=query[:60],
            )
        return result

    async def store_cache(
        self,
        query: str,
        response: str,
        org_id: str = "default",
        user_role: str = "default",
        acl_scope: str = "public",
        user_id: str | None = None,
        doc_ids: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Store query and response in L0 cache with cost savings estimation, RBAC and tenant isolation."""
        in_tokens = await self.estimate_tokens(query)
        out_tokens = await self.estimate_tokens(response)
        # GPT-4o baseline: $2.50 / 1M in, $10.00 / 1M out
        baseline_cost = (in_tokens * 2.50 / 1_000_000) + (out_tokens * 10.00 / 1_000_000)

        await self._cache.set(
            query=query,
            response=response,
            cost_saved=baseline_cost,
            org_id=org_id,
            user_role=user_role,
            acl_scope=acl_scope,
            user_id=user_id,
            doc_ids=doc_ids,
            tags=tags,
        )
        log.info("cache_stored", query=query[:60], org_id=org_id, user_role=user_role, saved_usd=baseline_cost)

    def invalidate_by_document(self, doc_id: str) -> int:
        """Purge all cache entries associated with a specific document ID."""
        return self._cache.invalidate_by_document(doc_id)

    def invalidate_by_tag(self, tag: str) -> int:
        """Purge cache entries matching a category tag."""
        return self._cache.invalidate_by_tag(tag)

    async def compress_prompt(self, prompt: str, budget: int) -> CompressedPrompt:
        """Coarse-to-fine token compression preserving technical terms and identifiers."""
        if len(prompt) > 4096:
            result = await asyncio.to_thread(self._compressor.compress, prompt, budget=budget)
        else:
            result = self._compressor.compress(prompt, budget=budget)
        if result.compression_ratio < 1.0:
            log.info(
                "prompt_compressed",
                original=result.original_tokens,
                compressed=result.compressed_tokens,
                ratio=round(result.compression_ratio, 2),
            )
        return result

    async def estimate_tokens(self, text: str) -> int:
        """Fast token estimation: ~1.3 tokens per word."""
        return max(1, int(len(text.split()) * 1.3))
