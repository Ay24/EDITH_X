"""Tests for Numerical & Entity Discrepancy Guards and RBAC Partitioning in Cache (Points 1 & 2)."""
import pytest
from edith_x.modules.optimization.cache import SemanticCache


@pytest.mark.asyncio
async def test_numerical_and_date_discrepancy_rejected():
    cache = SemanticCache(similarity_threshold=0.85)

    # Cache answer for Q3 2024 revenue
    await cache.set(
        query="What was our Q3 2024 revenue?",
        response="Q3 2024 revenue was $10M",
        cost_saved=0.01,
        org_id="org_finance",
    )

    # Identical structure but Q3 2025 revenue
    result = await cache.get(
        query="What was our Q3 2025 revenue?",
        org_id="org_finance",
    )
    # Must be a cache miss despite high n-gram overlap
    assert result.hit is False, "Q3 2025 query should NOT hit Q3 2024 cached response!"


@pytest.mark.asyncio
async def test_entity_discrepancy_rejected():
    cache = SemanticCache(similarity_threshold=0.85)

    await cache.set(
        query="Transfer $500 to Alice in finance department",
        response="Transaction to Alice initialized",
        cost_saved=0.01,
        org_id="org_payments",
    )

    # Bob instead of Alice
    result = await cache.get(
        query="Transfer $500 to Bob in finance department",
        org_id="org_payments",
    )
    assert result.hit is False, "Entity Bob should NOT hit cached response for Alice!"


@pytest.mark.asyncio
async def test_rbac_and_role_cache_isolation():
    cache = SemanticCache(similarity_threshold=0.85)

    # Admin stores a role-restricted answer
    await cache.set(
        query="What are the unannounced Q4 restructuring plans?",
        response="Confidential: 5% staff reduction in division X",
        cost_saved=0.05,
        org_id="org_01",
        user_role="executive",
        acl_scope="role_restricted",
    )

    # Junior employee in the same tenant asks the exact same question
    junior_result = await cache.get(
        query="What are the unannounced Q4 restructuring plans?",
        org_id="org_01",
        user_role="junior_contractor",
    )
    assert junior_result.hit is False, "Junior employee should NOT access executive cached response!"

    # Executive asks the same question
    exec_result = await cache.get(
        query="What are the unannounced Q4 restructuring plans?",
        org_id="org_01",
        user_role="executive",
    )
    assert exec_result.hit is True
    assert "Confidential" in exec_result.response


@pytest.mark.asyncio
async def test_document_and_tag_invalidation():
    cache = SemanticCache(similarity_threshold=0.85)

    # Set entry associated with doc_hr_404
    await cache.set(
        query="What is the severance package policy?",
        response="Standard severance is 2 weeks per year of service.",
        cost_saved=0.02,
        org_id="org_hr",
        doc_ids=["doc_hr_404"],
        tags=["hr_policy"],
    )

    # Verify hit before invalidation
    res_before = await cache.get("What is the severance package policy?", org_id="org_hr")
    assert res_before.hit is True

    # Invalidate document
    purged_count = cache.invalidate_by_document("doc_hr_404")
    assert purged_count == 1

    # Verify miss after invalidation
    res_after = await cache.get("What is the severance package policy?", org_id="org_hr")
    assert res_after.hit is False
