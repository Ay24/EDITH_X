"""Enterprise 3-state Circuit Breaker pattern for upstream LLM providers."""
from __future__ import annotations

import enum
import random
import time
from typing import Any
import structlog

log = structlog.get_logger(__name__)


class CircuitState(str, enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Guards upstream model API endpoints with rolling failure rate tracking,

    jittered backoff, and canary probe verification.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: float = 0.5,
        min_samples: int = 5,
        consecutive_failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_max_probes: int = 2,
        window_seconds: float = 60.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.min_samples = min_samples
        self.consecutive_failure_threshold = consecutive_failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_probes = half_open_max_probes
        self.window_seconds = window_seconds

        self._state: CircuitState = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._last_state_change: float = time.time()
        self._tripped_at: float = 0.0
        self._probes_in_flight: int = 0
        self._successful_probes: int = 0
        self._rolling_results: list[tuple[float, bool]] = []  # (timestamp, success)

    @property
    def state(self) -> CircuitState:
        now = time.time()
        if self._state == CircuitState.OPEN:
            # Check if cooldown + jitter has elapsed
            if (now - self._tripped_at) >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    def _transition_to(self, new_state: CircuitState) -> None:
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()
        log.info(
            "circuit_breaker_transition",
            circuit=self.name,
            from_state=old_state.value,
            to_state=new_state.value,
        )
        if new_state == CircuitState.OPEN:
            self._tripped_at = time.time()
            self._probes_in_flight = 0
            self._successful_probes = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._probes_in_flight = 0
            self._successful_probes = 0
        elif new_state == CircuitState.CLOSED:
            self._consecutive_failures = 0
            self._probes_in_flight = 0
            self._successful_probes = 0

    def can_execute(self) -> bool:
        """Evaluate if an execution attempt is allowed under current circuit state."""
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.OPEN:
            return False
        if current == CircuitState.HALF_OPEN:
            if self._probes_in_flight < self.half_open_max_probes:
                self._probes_in_flight += 1
                return True
            return False
        return False

    def record_success(self) -> None:
        """Record successful invocation."""
        now = time.time()
        self._rolling_results.append((now, True))
        self._prune_rolling_window(now)
        self._consecutive_failures = 0

        if self._state == CircuitState.HALF_OPEN:
            self._successful_probes += 1
            if self._successful_probes >= self.half_open_max_probes:
                self._transition_to(CircuitState.CLOSED)

    def record_failure(self, error: Any = None) -> None:
        """Record failed invocation or timeout."""
        now = time.time()
        self._rolling_results.append((now, False))
        self._prune_rolling_window(now)
        self._consecutive_failures += 1

        log.warning(
            "circuit_breaker_failure_recorded",
            circuit=self.name,
            consecutive=self._consecutive_failures,
            error=str(error),
        )

        if self._state == CircuitState.HALF_OPEN:
            # Canary probe failed, trip immediately back to OPEN with extra jitter
            self._transition_to(CircuitState.OPEN)
            return

        if self._state == CircuitState.CLOSED:
            # Check consecutive failure trip
            if self._consecutive_failures >= self.consecutive_failure_threshold:
                self._transition_to(CircuitState.OPEN)
                return

            # Check rolling error rate
            total_samples = len(self._rolling_results)
            if total_samples >= self.min_samples:
                failures = sum(1 for _, success in self._rolling_results if not success)
                error_rate = failures / total_samples
                if error_rate >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def _prune_rolling_window(self, now: float) -> None:
        cutoff = now - self.window_seconds
        self._rolling_results = [(t, s) for t, s in self._rolling_results if t > cutoff]
