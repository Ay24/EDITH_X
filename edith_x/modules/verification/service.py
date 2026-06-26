"""M11 — Verification: Confidence scoring and escalation logic."""
from __future__ import annotations
import structlog
from edith_x.core.config import Settings
from edith_x.core.interfaces import Context, ExecutionResult, VerificationResult

log = structlog.get_logger(__name__)


class VerificationService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def verify(self, result: ExecutionResult, context: Context) -> VerificationResult:
        response = result.response
        confidence = 0.9  # Default high confidence

        issues = []

        # Low confidence signals
        hedging_phrases = ["i'm not sure", "i don't know", "i cannot", "i'm unable", "unclear"]
        if any(phrase in response.lower() for phrase in hedging_phrases):
            confidence -= 0.3
            issues.append("Response contains uncertainty markers")

        if len(response) < 20:
            confidence -= 0.2
            issues.append("Response is very short")

        # Check grounding against knowledge chunks
        grounded = True
        if context.chunks and len(response) > 100:
            # Simple check: does response mention any source terms?
            chunk_words = set()
            for chunk in context.chunks[:3]:
                chunk_words.update(chunk.content.lower().split()[:20])
            response_words = set(response.lower().split())
            overlap = len(chunk_words & response_words)
            if overlap < 3:
                grounded = False
                confidence -= 0.1

        confidence = max(0.0, min(1.0, confidence))
        threshold = self._settings.escalation_confidence_threshold

        should_retry = confidence < 0.5
        escalate_to = None
        if 0.5 <= confidence < threshold and result.model_used:
            # Suggest escalation to stronger model
            if "mini" in result.model_used or "haiku" in result.model_used or "1b" in result.model_used:
                escalate_to = "gpt-4o"

        log.info("verification_complete", confidence=confidence, grounded=grounded, issues=issues)
        return VerificationResult(
            confidence=confidence,
            grounded=grounded,
            sources_verified=grounded,
            should_retry=should_retry,
            escalate_to=escalate_to,
            issues=issues,
        )
