"""Unit tests for semantic cache negation and directionality guardrails."""
from __future__ import annotations

import pytest
from edith_x.modules.optimization.cache import SemanticCache, _has_divergent_intent


def test_has_divergent_intent_detects_negations():
    assert _has_divergent_intent("Is mutual TLS enabled?", "Is mutual TLS not enabled?") is True
    assert _has_divergent_intent("Deploy without security checks", "Deploy with security checks") is True
    assert _has_divergent_intent("Never allow root login", "Always allow root login") is True
    assert _has_divergent_intent("How do I setup SSL?", "How can I setup SSL?") is False


def test_has_divergent_intent_detects_directionality():
    assert _has_divergent_intent("Transfer funds to Alice", "Transfer funds from Alice") is True
    assert _has_divergent_intent("Import data into cluster", "Export data out of cluster") is True
    assert _has_divergent_intent("Increase rate limit", "Decrease rate limit") is True


@pytest.mark.asyncio
async def test_semantic_cache_rejects_divergent_polarity_hit():
    cache = SemanticCache(similarity_threshold=0.80)
    await cache.set(
        "How do I transfer funds to Alice?",
        "Funds transfer initiated to Alice.",
        cost_saved=0.01,
    )

    # Opposite direction must NOT return cache hit despite high token overlap
    result_opposite = await cache.get("How do I transfer funds from Alice?")
    assert result_opposite.hit is False

    # Equivalent query should hit
    result_same = await cache.get("How can I transfer funds to Alice?")
    assert result_same.hit is True
    assert result_same.response == "Funds transfer initiated to Alice."
