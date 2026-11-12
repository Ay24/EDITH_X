import pytest
from edith_x.core.config import Settings
from edith_x.modules.optimization.cache import SemanticCache
from edith_x.modules.optimization.service import OptimizationService

@pytest.mark.asyncio
async def test_exact_hash_cache_hit():
    cache = SemanticCache(similarity_threshold=0.92)
    await cache.set("What is the capital of France?", "Paris", cost_saved=0.002)
    
    result = await cache.get("What is the capital of France?")
    assert result.hit is True
    assert result.response == "Paris"
    assert result.saved_cost_usd == 0.002

@pytest.mark.asyncio
async def test_exact_hash_normalization_hit():
    cache = SemanticCache(similarity_threshold=0.92)
    await cache.set("  What is the capital of France?  ", "Paris", cost_saved=0.002)
    
    result = await cache.get("what is the capital of france?")
    assert result.hit is True
    assert result.response == "Paris"

@pytest.mark.asyncio
async def test_semantic_similarity_cache_hit():
    cache = SemanticCache(similarity_threshold=0.85)
    await cache.set("How do I reset my account password?", "Click on the forgot password link.", cost_saved=0.003)
    
    result = await cache.get("How can I reset my account password?")
    assert result.hit is True
    assert result.response == "Click on the forgot password link."

@pytest.mark.asyncio
async def test_cache_miss_on_dissimilar_query():
    cache = SemanticCache(similarity_threshold=0.92)
    await cache.set("Tell me a joke about dogs", "Why do dogs wear shoes?", cost_saved=0.001)
    
    result = await cache.get("Explain quantum entanglement physics in detail")
    assert result.hit is False
    assert result.response == ""

@pytest.mark.asyncio
async def test_optimization_service_end_to_end():
    svc = OptimizationService(Settings())
    # Initially miss
    res1 = await svc.check_cache("What are the quarterly financial results?")
    assert res1.hit is False
    
    # Store
    await svc.store_cache("What are the quarterly financial results?", "Revenue grew 18% year-over-year.")
    
    # Second check hit
    res2 = await svc.check_cache("what are the quarterly financial results?")
    assert res2.hit is True
    assert res2.response == "Revenue grew 18% year-over-year."
    assert res2.saved_cost_usd > 0.0
