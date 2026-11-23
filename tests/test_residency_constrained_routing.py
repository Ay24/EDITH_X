"""Tests for Policy-Constrained Failover and Data Residency (Point 9)."""
import pytest
from edith_x.core.config import Settings
from edith_x.core.interfaces import Context, IntentResult, PolicyDecision, ModelSelection
from edith_x.modules.router.service import RouterService
from edith_x.modules.execution.service import ExecutionService


@pytest.mark.asyncio
async def test_router_restricts_to_sovereign_models_for_eu_residency():
    settings = Settings(
        local_models="llama-3.2-3b-instruct",
        cloud_models="gpt-4o,claude-sonnet-4-5",
    )
    router = RouterService(settings)

    ctx = Context(query="Analyze EU citizen data")
    policy = PolicyDecision(
        allowed_models=["gpt-4o", "claude-sonnet-4-5", "llama-3.2-3b-instruct"],
        requires_local=False,
        data_residency="eu",
    )
    intent = IntentResult(
        type="task",
        domain="legal",
        risk=0.2,
        estimated_cost_usd=0.01,
        complexity=0.5,
        confidence=0.9,
    )

    selection = await router.route(ctx, policy, intent)

    # Must select local/sovereign model, never US public cloud
    assert selection.provider == "local_llm"
    assert "llama" in selection.model
    assert "residency" in selection.reasoning.lower() or "sovereign" in selection.reasoning.lower()


def test_execution_fallback_strictly_respects_data_residency():
    settings = Settings(
        openai_api_key="sk-test-valid-key-12345",
        anthropic_api_key="sk-ant-test-valid-key-12345",
        local_models="llama-3.2-3b-instruct",
    )
    service = ExecutionService(settings)

    # When data residency is EU/local, US cloud models must NOT be present in fallback candidates
    fallbacks_eu = service._get_fallback_candidates(
        primary_provider="local_llm",
        primary_model="llama-3.2-3b-instruct",
        data_residency="eu",
    )
    # Should be empty or only other local models, definitely NO US cloud models
    providers = [c[0] for c in fallbacks_eu]
    assert "openai" not in providers
    assert "anthropic" not in providers
    assert "groq" not in providers
