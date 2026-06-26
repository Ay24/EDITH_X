"""M9 — Model Router: Cost/latency/policy-aware model selection across 4 layers."""
from __future__ import annotations

import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import Context, IntentResult, ModelSelection, PolicyDecision

log = structlog.get_logger(__name__)

# Cost per 1K tokens (input) — approximate
_MODEL_COSTS: dict[str, float] = {
    "nvidia_nim/meta/llama-3.1-8b-instruct": 0.0001,
    "nvidia_nim/meta/llama-3.1-405b-instruct": 0.005,
    "gpt-4o-mini": 0.00015,
    "gpt-4o": 0.0025,
    "claude-3-5-haiku-20241022": 0.0008,
    "claude-sonnet-4-5": 0.003,
    "gemini-1.5-flash": 0.000075,
    "gemini-1.5-pro": 0.00125,
}

_MODEL_LATENCY: dict[str, int] = {
    "nvidia_nim/meta/llama-3.1-8b-instruct": 600,
    "nvidia_nim/meta/llama-3.1-405b-instruct": 2500,
    "gpt-4o-mini": 2000,
    "gpt-4o": 4000,
    "claude-3-5-haiku-20241022": 2500,
    "claude-sonnet-4-5": 5000,
    "gemini-1.5-flash": 1500,
    "gemini-1.5-pro": 3000,
}


class RouterService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def route(
        self,
        context: Context,
        policy: PolicyDecision,
        intent: IntentResult,
    ) -> ModelSelection:
        if policy.requires_local or (
            intent.complexity < 0.5
        ):
            # Hackathon: Shifted L1 Local to NVIDIA Fast Tier for cloud hosting
            model = "nvidia_nim/meta/llama-3.1-8b-instruct"
            log.info("routed_to_fast_tier", model=model, reason="complexity_low_or_policy")
            return ModelSelection(
                provider="nvidia_nim",
                model=model,
                reasoning=f"NVIDIA Fast Tier selected: complexity={intent.complexity:.2f}",
                estimated_cost_usd=_MODEL_COSTS.get(model, 0.0),
                estimated_latency_ms=_MODEL_LATENCY.get(model, 600),
                layer="L1_local", # Kept as L1_local for graph UI compatibility
            )

        # L2/L3: Cloud routing
        if not self._settings.has_cloud_models:
            # Fallback to local even for complex tasks
            local = self._settings.local_model_list
            model = local[0] if local else "llama-3.2-3b-instruct"
            return ModelSelection(
                provider="local_llm",
                model=model,
                reasoning="No cloud keys configured, using local fallback",
                estimated_cost_usd=0.0,
                estimated_latency_ms=_MODEL_LATENCY.get(model, 2000),
                layer="L1_local",
            )

        # Select best cloud model based on complexity + allowed list
        allowed = policy.allowed_models or self._settings.cloud_model_list
        cloud_available = [m for m in self._settings.cloud_model_list if m in allowed]

        if intent.complexity < 0.6:
            # Use cheaper/faster model
            preferred = ["nvidia_nim/meta/llama-3.1-8b-instruct", "gpt-4o-mini", "claude-3-5-haiku-20241022"]
        else:
            # Use smarter model
            preferred = ["nvidia_nim/meta/llama-3.1-405b-instruct", "gpt-4o"]

        model = next((m for m in preferred if m in cloud_available), "nvidia_nim/meta/llama-3.1-405b-instruct")
        provider = self._infer_provider(model)

        log.info("routed_to_cloud", model=model, complexity=intent.complexity)
        return ModelSelection(
            provider=provider,
            model=model,
            reasoning=f"Cloud model: complexity={intent.complexity:.2f}, type={intent.type}",
            estimated_cost_usd=_MODEL_COSTS.get(model, 0.001) * context.token_count / 1000,
            estimated_latency_ms=_MODEL_LATENCY.get(model, 3000),
            layer="L3_cloud",
        )

    def _infer_provider(self, model: str) -> str:
        if "nvidia" in model:
            return "nvidia_nim"
        if "gpt" in model or "o1" in model:
            return "openai"
        if "claude" in model:
            return "anthropic"
        if "gemini" in model:
            return "google"
        if "llama" in model or "mistral" in model:
            return "local_llm"
        return "openai"
