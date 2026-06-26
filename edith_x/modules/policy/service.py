"""M4 — Policy Engine: Evaluates enterprise policies before any AI call."""
from __future__ import annotations

import re
import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext, IntentResult, PolicyDecision

log = structlog.get_logger(__name__)

# PII patterns
_PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),           # SSN
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Email
    re.compile(r"\b4[0-9]{12}(?:[0-9]{3})?\b"),       # Visa card
    re.compile(r"\b\d{10,11}\b"),                      # Phone
]

# Domain-based policy rules
_DOMAIN_POLICIES: dict[str, dict] = {
    "legal": {
        "requires_local": False,
        "allowed_models": ["gpt-4o", "claude-sonnet-4-5"],
        "data_residency": "us",
    },
    "medical": {
        "requires_local": True,
        "requires_human_approval": True,
        "allowed_models": [],  # local only
        "data_residency": "local",
    },
    "customer_support": {
        "requires_local": True,
        "allowed_models": ["llama3.2:3b"],
        "data_residency": "any",
    },
    "engineering": {
        "requires_local": False,
        "allowed_models": [],  # any
        "data_residency": "any",
    },
}


class PolicyService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _detect_pii(self, text: str) -> bool:
        return any(p.search(text) for p in _PII_PATTERNS)

    async def evaluate(self, intent: IntentResult, ctx: AuthContext) -> PolicyDecision:
        # Start permissive, restrict based on rules
        decision = PolicyDecision(
            allowed_models=self._settings.cloud_model_list + self._settings.local_model_list,
            requires_local=False,
            requires_human_approval=False,
            pii_detected=False,
            data_residency="any",
            blocked=False,
        )

        # Block very high risk intents that need human approval
        if intent.risk > 0.8:
            decision.requires_human_approval = True

        # Block if cost exceeds limit
        if intent.estimated_cost_usd > self._settings.max_cost_per_request_usd:
            decision.blocked = True
            decision.block_reason = (
                f"Estimated cost ${intent.estimated_cost_usd:.4f} exceeds "
                f"limit ${self._settings.max_cost_per_request_usd:.2f}"
            )

        log.info(
            "policy_evaluated",
            blocked=decision.blocked,
            requires_local=decision.requires_local,
            pii=decision.pii_detected,
        )
        return decision
