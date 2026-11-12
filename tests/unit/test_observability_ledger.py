import pytest
from edith_x.core.config import Settings
from edith_x.core.interfaces import PipelineEvent
from edith_x.modules.observability.service import ObservabilityService

@pytest.mark.asyncio
async def test_cost_savings_calculation_and_ledger():
    obs = ObservabilityService(Settings())
    event = PipelineEvent(
        run_id="run-1",
        org_id="org-1",
        user_id="user-1",
        model_selected="llama-3.2-3b",
        provider="local_llm",
        cache_hit=False,
        tokens_input=1000,
        tokens_output=500,
        cost_usd=0.0,
        cost_saved_usd=0.0075,
        latency_ms=120,
        layer="L1_local"
    )
    await obs.record(event)
    assert obs.get_cumulative_savings() >= 0.0075
    assert obs.get_cumulative_cost() == 0.0

    metrics = await obs.get_metrics("org-1")
    assert metrics.total_requests == 1
    assert metrics.total_saved_usd >= 0.0075
    assert metrics.layer_distribution.get("L1_local") == 1

@pytest.mark.asyncio
async def test_prometheus_metrics_export():
    obs = ObservabilityService(Settings())
    event = PipelineEvent(
        run_id="run-2",
        org_id="org-1",
        user_id="user-1",
        model_selected="gpt-4o-mini",
        provider="openai",
        cache_hit=True,
        tokens_input=200,
        tokens_output=100,
        cost_usd=0.0,
        cost_saved_usd=0.0015,
        latency_ms=18,
        layer="L0_cache"
    )
    await obs.record(event)
    prom_text = obs.generate_prometheus_metrics()
    assert "edith_requests_total" in prom_text
    assert "edith_cost_saved_usd_total" in prom_text
    assert "edith_cost_usd_total" in prom_text
