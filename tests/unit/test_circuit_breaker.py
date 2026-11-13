"""Unit tests for 3-state enterprise circuit breaker."""
from __future__ import annotations

import time
import pytest
from edith_x.modules.gateway.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_breaker_starts_closed():
    cb = CircuitBreaker("provider_nim", failure_threshold=0.5, min_samples=3, recovery_timeout=0.2)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True


def test_circuit_breaker_trips_to_open_on_consecutive_failures():
    cb = CircuitBreaker("provider_nim", consecutive_failure_threshold=3, recovery_timeout=0.2)
    
    cb.record_failure("timeout 1")
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    cb.record_failure("timeout 2")
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    cb.record_failure("timeout 3")
    # Must trip to OPEN
    assert cb.state == CircuitState.OPEN
    # Immediate execution blocked
    assert cb.can_execute() is False


def test_circuit_breaker_trips_on_error_rate():
    cb = CircuitBreaker("provider_openai", failure_threshold=0.5, min_samples=4, recovery_timeout=0.2)
    
    cb.record_success()
    cb.record_failure("500 internal server error")
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    
    cb.record_failure("503 service unavailable")
    # 2 failures out of 4 samples = 50% >= failure_threshold (0.5)
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False


def test_circuit_breaker_half_open_recovery():
    cb = CircuitBreaker(
        "provider_anthropic",
        consecutive_failure_threshold=2,
        recovery_timeout=0.1,
        half_open_max_probes=2,
    )
    
    cb.record_failure("err 1")
    cb.record_failure("err 2")
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # Wait for recovery timeout
    time.sleep(0.12)
    
    # State should shift to HALF_OPEN upon probe attempt
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN
    
    # Successful canary 1
    cb.record_success()
    assert cb.state == CircuitState.HALF_OPEN
    
    # Successful canary 2
    assert cb.can_execute() is True
    cb.record_success()
    
    # Circuit resets to CLOSED
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True


def test_circuit_breaker_half_open_failure_reverts_to_open():
    cb = CircuitBreaker(
        "provider_anthropic",
        consecutive_failure_threshold=2,
        recovery_timeout=0.1,
        half_open_max_probes=2,
    )
    
    cb.record_failure("err 1")
    cb.record_failure("err 2")
    assert cb.state == CircuitState.OPEN
    
    time.sleep(0.12)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN
    
    # Canary fails
    cb.record_failure("canary failed")
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False
