"""M12 — Reflection: Post-execution analysis for iterative improvement."""
from __future__ import annotations
import structlog
from edith_x.core.config import Settings
from edith_x.core.interfaces import ExecutionResult, ReflectionNote, VerificationResult

log = structlog.get_logger(__name__)


class ReflectionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def reflect(
        self,
        goal: str,
        result: ExecutionResult,
        verification: VerificationResult,
    ) -> ReflectionNote:
        action = "accept"
        observation = "Response meets quality threshold"
        suggestion = "No changes needed"

        if verification.should_retry:
            action = "retry"
            observation = f"Low confidence: {verification.confidence:.2f}. Issues: {', '.join(verification.issues)}"
            suggestion = "Retry with better context or stronger model"
        elif not verification.grounded and result.model_used:
            action = "replan"
            observation = "Response not grounded in retrieved knowledge"
            suggestion = "Retrieve more specific knowledge sources before responding"
        elif verification.escalate_to:
            action = "retry"
            observation = f"Confidence {verification.confidence:.2f} below threshold, escalating"
            suggestion = f"Use {verification.escalate_to} for better accuracy"

        log.info("reflection_complete", action=action, confidence=verification.confidence)
        return ReflectionNote(observation=observation, suggestion=suggestion, action=action)
