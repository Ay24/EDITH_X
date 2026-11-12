"""M9 — Model Router: Cost/latency/policy-aware model selection across 4 layers."""
from __future__ import annotations

import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import Context, IntentResult, ModelSelection, PolicyDecision
from edith_x.modules.router.pareto import ParetoModelRouter

log = structlog.get_logger(__name__)

# Cost per 1K tokens (input)
_MODEL_COSTS: dict[str, float] = {
    "nvidia_nim/meta/llama-3.1-8b-instruct": 0.0001,
    "nvidia_nim/meta/llama-3.1-70b-instruct": 0.0008,
    "gpt-4o-mini": 0.00015,
    "gpt-4o": 0.0025,
    "claude-3-5-haiku-20241022": 0.0008,
    "claude-sonnet-4-5": 0.003,
}

_MODEL_LATENCY: dict[str, int] = {
    "nvidia_nim/meta/llama-3.1-8b-instruct": 400,
    "nvidia_nim/meta/llama-3.1-70b-instruct": 1100,
    "gpt-4o-mini": 1200,
    "gpt-4o": 3000,
    "llama-3.2-3b-instruct": 250,
}


class RouterService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pareto = ParetoModelRouter(threshold_cheap=0.50, threshold_medium=0.25)

    async def route(
        self,
        context: Context,
        policy: PolicyDecision,
        intent: IntentResult,
    ) -> ModelSelection:
        # 1. Policy Constraint: Air-gapped / PII detected
        if policy.requires_local:
            local = self._settings.local_model_list
            model = local[0] if local else "llama-3.2-3b-instruct"
            log.info("policy_enforcing_local_tier", model=model)
            return ModelSelection(
                provider="local_llm",
                model=model,
                reasoning="Policy firewall requires local on-premise model",
                estimated_cost_usd=0.0,
                estimated_latency_ms=_MODEL_LATENCY.get(model, 250),
                layer="L1_local",
            )

        # 2. Calibrated Pareto Route Selection
        pareto_tier = self._pareto.select_tier(context.query)
        cheap_prob = self._pareto.predict_cheap_capability(context.query)

        if pareto_tier == "L1_local":
            model = "nvidia_nim/meta/llama-3.1-8b-instruct"
            log.info("routed_to_fast_tier", model=model, p_cheap=cheap_prob)
            return ModelSelection(
                provider="nvidia_nim",
                model=model,
                reasoning=f"Calibrated Pareto router: P(cheap)={cheap_prob:.2f} >= 0.50",
                estimated_cost_usd=_MODEL_COSTS.get(model, 0.0001),
                estimated_latency_ms=_MODEL_LATENCY.get(model, 400),
                layer="L1_local",
            )
        elif pareto_tier == "L2_compressed":
            model = "nvidia_nim/meta/llama-3.1-70b-instruct"
            log.info("routed_to_medium_tier", model=model, p_cheap=cheap_prob)
            return ModelSelection(
                provider="nvidia_nim",
                model=model,
                reasoning=f"Calibrated Pareto router: 0.25 <= P(cheap)={cheap_prob:.2f} < 0.50",
                estimated_cost_usd=_MODEL_COSTS.get(model, 0.0008),
                estimated_latency_ms=_MODEL_LATENCY.get(model, 1100),
                layer="L2_compressed",
            )
        else:
            # L3 Flagship Cloud
            if self._settings.openai_api_key:
                provider = "openai"
                model = "gpt-4o"
            elif self._settings.nvidia_api_key:
                provider = "nvidia_nim"
                model = "nvidia_nim/meta/llama-3.1-70b-instruct"
            else:
                provider = "local_llm"
                model = self._settings.local_model_list[0] if self._settings.local_model_list else "llama-3.2-3b-instruct"

            log.info("routed_to_frontier_cloud", model=model, p_cheap=cheap_prob)
            return ModelSelection(
                provider=provider,
                model=model,
                reasoning=f"High complexity reasoning task: P(cheap)={cheap_prob:.2f} < 0.25",
                estimated_cost_usd=_MODEL_COSTS.get(model, 0.0025),
                estimated_latency_ms=_MODEL_LATENCY.get(model, 3000),
                layer="L3_cloud",
            )
