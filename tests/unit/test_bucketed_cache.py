"""Unit tests for inverted bucketed vector index and two-tier cache synchronization."""
from __future__ import annotations

import pytest
from edith_x.modules.optimization.cache import SemanticCache, InMemoryL2Store, CacheEntry


@pytest.mark.asyncio
async def test_inverted_bucketed_candidate_filtering():
    """Verify that inverted index accurately surfaces semantic matches without scanning unrelated keys."""
    cache = SemanticCache(similarity_threshold=0.85, max_entries=500)
    
    # Populate cache with varied domain queries
    await cache.set("How do I configure postgresql ssl certificates?", "Guide to postgres SSL", cost_saved=0.01)
    await cache.set("Explain byzantine fault tolerance in distributed consensus", "BFT explained", cost_saved=0.02)
    await cache.set("How to write a fast api route with dependency injection", "FastAPI DI guide", cost_saved=0.015)
    
    # Query with semantic variant of postgres question
    result = await cache.get("How can I configure postgresql ssl certificates?")
    assert result.hit is True
    assert "Guide to postgres SSL" in result.response
    assert result.similarity >= 0.85
    
    # Query with completely unrelated question
    unrelated = await cache.get("What is the recipe for chocolate cake?")
    assert unrelated.hit is False


@pytest.mark.asyncio
async def test_two_tier_cache_l2_fallback():
    """Verify that when an item misses L1 (e.g. cold pod restart), it retrieves from L2."""
    l2_store = InMemoryL2Store()
    
    # Pod A initializes and sets an item
    pod_a_cache = SemanticCache(l2_backend=l2_store)
    await pod_a_cache.set("What are the quarterly financial projections?", "Revenue: $10M, EBITDA: $2.5M", cost_saved=0.05)
    
    # Pod B starts cold with empty L1 cache, but sharing the same L2 store
    pod_b_cache = SemanticCache(l2_backend=l2_store)
    
    # Exact lookup in Pod B should fetch from L2 store
    result = await pod_b_cache.get("What are the quarterly financial projections?")
    assert result.hit is True
    assert "Revenue: $10M" in result.response
    assert result.saved_cost_usd == 0.05


@pytest.mark.asyncio
async def test_lru_eviction_cleans_inverted_index():
    """Verify that when entries exceed max_entries, oldest entries and inverted postings are purged."""
    cache = SemanticCache(similarity_threshold=0.90, max_entries=3)
    
    await cache.set("Query Alpha", "Response A", cost_saved=0.001)
    await cache.set("Query Beta", "Response B", cost_saved=0.001)
    await cache.set("Query Gamma", "Response C", cost_saved=0.001)
    
    # 4th query causes Query Alpha to be evicted
    await cache.set("Query Delta", "Response D", cost_saved=0.001)
    
    res_alpha = await cache.get("Query Alpha")
    assert res_alpha.hit is False
    
    res_delta = await cache.get("Query Delta")
    assert res_delta.hit is True
