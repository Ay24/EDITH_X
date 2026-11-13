"""M4 — Policy Engine: Evaluates enterprise policies before any AI call."""
from __future__ import annotations

import asyncio
import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext, IntentResult, PolicyDecision
from edith_x.modules.policy.firewall import PIIFirewall

log = structlog.get_logger(__name__)

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
        self._firewall = PIIFirewall()

    def sanitize_payload(self, text: str) -> tuple[str, bool, list[str]]:
        """Redact PII/secrets from text."""
        return self._firewall.redact(text)

    async def evaluate(self, intent: IntentResult, ctx: AuthContext, query: str = "") -> PolicyDecision:
        # Check PII in query or intent context
        check_text = f"{query} {getattr(intent, 'summary', '')}".strip()
        if not check_text:
            pii_detected, pii_types = False, []
        elif len(check_text) > 4096:
            _, pii_detected, pii_types = await asyncio.to_thread(self._firewall.redact, check_text)
        else:
            _, pii_detected, pii_types = self._firewall.redact(check_text)

        # Start permissive, restrict based on rules
        decision = PolicyDecision(
            allowed_models=self._settings.cloud_model_list + self._settings.local_model_list,
            requires_local=pii_detected,
            requires_human_approval=False,
            pii_detected=pii_detected,
            data_residency="local" if pii_detected else "any",
            blocked=False,
        )

        # If PII detected, lock down models to local only
        if pii_detected:
            decision.allowed_models = list(self._settings.local_model_list)
            decision.requires_local = True
            log.warning("pii_detected_enforcing_local", detected=pii_types)

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
