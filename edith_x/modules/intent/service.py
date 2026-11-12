"""M3 — Intent Engine: Classifies query type, complexity, risk, and cost estimate."""
from __future__ import annotations

import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext, IntentResult
from edith_x.modules.intent.router import CentroidIntentRouter

log = structlog.get_logger(__name__)

_COMPLEXITY_SIGNALS = {
    "high": ["enterprise", "production", "multi-step", "complex", "architecture", "system", "distributed", "kubernetes"],
    "medium": ["integrate", "connect", "configure", "setup", "build", "refactor", "optimize"],
    "low": ["simple", "quick", "basic", "single", "what is", "hello", "hi"],
}

_COST_MAP = {
    "question": 0.001,
    "retrieval": 0.002,
    "summarization": 0.003,
    "analysis": 0.008,
    "coding": 0.010,
    "planning": 0.012,
    "automation": 0.015,
    "security": 0.010,
    "task": 0.005,
}

_RISK_MAP = {
    "security": 0.7,
    "automation": 0.5,
    "coding": 0.3,
    "planning": 0.2,
    "analysis": 0.2,
    "retrieval": 0.1,
    "summarization": 0.1,
    "question": 0.05,
    "task": 0.2,
}


class IntentService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._router = CentroidIntentRouter()

    async def classify(self, query: str, ctx: AuthContext) -> IntentResult:
        query_lower = query.lower()

        # 1. Sub-2ms Centroid Vector Classification
        intent_type = self._router.classify(query)

        # 2. Complexity Scoring
        complexity = 0.4  # default medium
        for kw in _COMPLEXITY_SIGNALS["high"]:
            if kw in query_lower:
                complexity = max(complexity, 0.8)
        for kw in _COMPLEXITY_SIGNALS["medium"]:
            if kw in query_lower and complexity < 0.8:
                complexity = max(complexity, 0.6)
        for kw in _COMPLEXITY_SIGNALS["low"]:
            if kw in query_lower and complexity == 0.4:
                complexity = 0.2

        if len(query.split()) > 100:
            complexity = min(1.0, complexity + 0.2)

        risk = _RISK_MAP.get(intent_type, 0.2)
        if "delete" in query_lower or "drop database" in query_lower or "rm -rf" in query_lower:
            risk = 0.95

        cost_est = _COST_MAP.get(intent_type, 0.005) * (1 + complexity)

        log.info(
            "intent_classified",
            type=intent_type,
            complexity=complexity,
            risk=risk,
            query=query[:60],
        )

        return IntentResult(
            type=intent_type,
            complexity=complexity,
            risk=risk,
            estimated_cost_usd=round(cost_est, 5),
            confidence=0.92,
            latency_requirement_ms=2000 if complexity > 0.7 else 800,
        )
