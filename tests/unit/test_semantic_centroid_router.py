"""Unit tests for hybrid semantic centroid Pareto model router."""
from __future__ import annotations

import pytest
from edith_x.modules.router.pareto import ParetoModelRouter


def test_fast_path_bypass_clear_cases():
    router = ParetoModelRouter()
    
    # Obvious simple query
    p_simple = router.predict_cheap_capability("What is the capital of Japan?")
    assert p_simple >= 0.70
    assert router.select_tier("What is the capital of Japan?") in ("L1_local", "L2_compressed")
    
    # Obvious complex query
    p_complex = router.predict_cheap_capability("Prove the formal undecidability of the halting problem in byzantine consensus")
    assert p_complex <= 0.35
    assert router.select_tier("Prove the formal undecidability of the halting problem in byzantine consensus") == "L3_cloud"


def test_centroid_similarity_resolves_borderline_queries():
    router = ParetoModelRouter()
    
    # Ambiguous query without obvious single keywords but dense technical engineering terminology
    query_borderline_complex = "Investigate anomalous latencies and memory allocation spikes across distributed workers"
    p_score = router.predict_cheap_capability(query_borderline_complex)
    
    # Semantic centroid should recognize this as complex engineering workload
    tier = router.select_tier(query_borderline_complex)
    assert tier in ("L2_compressed", "L3_cloud")
    
    # Another borderline query with conversational/simple semantics
    query_borderline_simple = "Can you rephrase this meeting note into bullet points for the team?"
    p_simple_score = router.predict_cheap_capability(query_borderline_simple)
    assert p_simple_score > p_score


def test_budget_aware_tier_threshold_modulation():
    router = ParetoModelRouter()
    borderline_query = "Provide architectural feedback on the proposed database schema migration"
    
    # Under cost_saver budget pressure, prefer cheaper tier
    tier_cost_saver = router.select_tier(borderline_query, budget_mode="cost_saver")
    assert tier_cost_saver in ("L1_local", "L2_compressed")
    
    # Under quality_first budget, route to flagship
    tier_quality = router.select_tier(borderline_query, budget_mode="quality_first")
    assert tier_quality in ("L2_compressed", "L3_cloud")
