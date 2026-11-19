"""Unit test for tenant-partitioned semantic and exact cache isolation (BUG-004)."""
import pytest
from edith_x.modules.optimization.cache import SemanticCache


@pytest.mark.asyncio
async def test_semantic_cache_tenant_partitioning():
    cache = SemanticCache(similarity_threshold=0.85)

    # Tenant A caches internal proprietary financial info
    await cache.set(
        query="What is our internal Q3 bonus multiplier?",
        response="Tenant A bonus multiplier is 2.5x for engineering.",
        cost_saved=0.005,
        org_id="org_alpha",
    )

    # 1. Exact match probe from Tenant B must MISS
    res_b_exact = await cache.get(
        query="What is our internal Q3 bonus multiplier?",
        org_id="org_beta",
    )
    assert res_b_exact.hit is False
    assert res_b_exact.response == ""

    # 2. Semantic probe from Tenant B must MISS
    res_b_semantic = await cache.get(
        query="Tell me the Q3 internal bonus multiplier",
        org_id="org_beta",
    )
    assert res_b_semantic.hit is False
    assert res_b_semantic.response == ""

    # 3. Exact match probe from Tenant A must HIT
    res_a_exact = await cache.get(
        query="What is our internal Q3 bonus multiplier?",
        org_id="org_alpha",
    )
    assert res_a_exact.hit is True
    assert "2.5x" in res_a_exact.response

    # 4. Semantic paraphrase probe from Tenant A must HIT
    res_a_semantic = await cache.get(
        query="What is our internal Q3 bonus multiplier",
        org_id="org_alpha",
    )
    assert res_a_semantic.hit is True
    assert "2.5x" in res_a_semantic.response
