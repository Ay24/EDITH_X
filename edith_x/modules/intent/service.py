"""M3 — Intent Engine: Classifies query type, complexity, risk, and cost estimate."""
from __future__ import annotations

import re
import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext, IntentResult

log = structlog.get_logger(__name__)

# Keyword-based intent patterns (Phase 0 — no LLM needed)
_PATTERNS: list[tuple[list[str], str]] = [
    (["write code", "implement", "create function", "debug", "fix bug", "refactor"], "coding"),
    (["search", "find", "look up", "retrieve", "fetch", "list all"], "retrieval"),
    (["summarize", "summary", "tldr", "brief", "overview"], "summarization"),
    (["analyze", "analyse", "evaluate", "assess", "compare", "audit"], "analysis"),
    (["plan", "roadmap", "strategy", "schedule", "organize"], "planning"),
    (["automate", "run", "execute", "deploy", "trigger", "schedule"], "automation"),
    (["secure", "vulnerability", "exploit", "pentest", "security"], "security"),
    (["what", "why", "how", "when", "who", "explain", "define"], "question"),
]

_COMPLEXITY_SIGNALS = {
    "high": ["enterprise", "production", "multi-step", "complex", "architecture", "system"],
    "medium": ["integrate", "connect", "configure", "setup", "build"],
    "low": ["simple", "quick", "basic", "single", "what is"],
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


class IntentService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def classify(self, query: str, ctx: AuthContext) -> IntentResult:
        query_lower = query.lower()

        # Detect type
        intent_type = "task"
        for keywords, itype in _PATTERNS:
            if any(kw in query_lower for kw in keywords):
                intent_type = itype
                break

        # Estimate complexity
        complexity = 0.4  # default medium
        for kw in _COMPLEXITY_SIGNALS["high"]:
            if kw in query_lower:
                complexity = 0.8
                break
        for kw in _COMPLEXITY_SIGNALS["low"]:
            if kw in query_lower:
                complexity = 0.2
                break

        # Estimate risk
        risk = 0.1
        if intent_type in ("security", "automation"):
            risk = 0.7
        elif intent_type in ("coding",):
            risk = 0.3

        estimated_cost = _COST_MAP.get(intent_type, 0.005) * (1 + complexity)

        # Latency: simple questions need fast responses
        latency_req = 2000 if complexity < 0.4 else 10000

        result = IntentResult(
            type=intent_type,
            complexity=complexity,
            risk=risk,
            estimated_cost_usd=estimated_cost,
            confidence=0.85,
            latency_requirement_ms=latency_req,
        )
        log.info("intent_classified", type=result.type, complexity=complexity)
        return result
