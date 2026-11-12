# EDITH-X Enterprise Production Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform EDITH-X into a production-grade, highly reliable, hybrid enterprise AI runtime featuring real L0 semantic caching, self-healing multi-provider fallback cascades, automated PII firewalling, verifiable token ROI metrics, and end-to-end test coverage.

**Architecture:** 
A dual-entry gateway (standard OpenAI `/v1/chat/completions` proxy and autonomous `/edith/v1/run` goal engine) passing payloads through an on-premise PII redaction policy filter, an embedding-backed dual semantic cache (L0), and an intelligent 4-tier cost router with circuit breakers and multi-provider failover cascades. All telemetry is recorded to a verifiable savings ledger exposing Prometheus metrics.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic V2, LiteLLM, LangGraph, pytest, structlog.

---

### Task 1: Real L0 Dual Semantic Cache (Exact Hash + Cosine Embedding Cache)

**Files:**
- Create: `edith_x/modules/optimization/cache.py`
- Modify: `edith_x/modules/optimization/service.py`
- Test: `tests/unit/test_semantic_cache.py`

- [ ] **Step 1: Write the failing unit tests for exact and semantic cache**

```python
# tests/unit/test_semantic_cache.py
import pytest
from edith_x.modules.optimization.cache import SemanticCache

@pytest.mark.asyncio
async def test_exact_hash_cache_hit():
    cache = SemanticCache(similarity_threshold=0.92)
    await cache.set("What is the capital of France?", "Paris", cost_saved=0.002)
    
    result = await cache.get("What is the capital of France?")
    assert result.hit is True
    assert result.response == "Paris"
    assert result.saved_cost_usd == 0.002

@pytest.mark.asyncio
async def test_semantic_similarity_cache_hit():
    cache = SemanticCache(similarity_threshold=0.90)
    await cache.set("How do I reset my account password?", "Click on forgot password link.", cost_saved=0.003)
    
    result = await cache.get("How can I reset my password?")
    assert result.hit is True
    assert result.response == "Click on forgot password link."

@pytest.mark.asyncio
async def test_cache_miss_on_dissimilar_query():
    cache = SemanticCache(similarity_threshold=0.92)
    await cache.set("Tell me a joke about dogs", "Why do dogs wear shoes?", cost_saved=0.001)
    
    result = await cache.get("Explain quantum entanglement physics")
    assert result.hit is False
    assert result.response == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/unit/test_semantic_cache.py -v`
Expected: FAIL (ModuleNotFoundError / SemanticCache not defined)

- [ ] **Step 3: Implement `SemanticCache` and update `OptimizationService`**

Implement `edith_x/modules/optimization/cache.py` with fast token normalization, SHA-256 exact matching, character n-gram / embedding vector cosine similarity with LRU eviction and TTL. Wire into `OptimizationService.check_cache` and `OptimizationService.store_cache`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/unit/test_semantic_cache.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add edith_x/modules/optimization/ tests/unit/test_semantic_cache.py
git commit -m "feat(optimization): implement real L0 exact and semantic cache engine"
```

---

### Task 2: PII Redaction & Token Firewall

**Files:**
- Create: `edith_x/modules/policy/firewall.py`
- Modify: `edith_x/modules/policy/service.py`
- Test: `tests/unit/test_pii_firewall.py`

- [ ] **Step 1: Write the failing unit tests for PII and Secret detection**

```python
# tests/unit/test_pii_firewall.py
from edith_x.modules.policy.firewall import PIIFirewall

def test_detect_and_mask_credit_card():
    firewall = PIIFirewall()
    text = "My corporate card is 4532-1234-5678-9012 for billing"
    cleaned, detected = firewall.redact(text)
    assert detected is True
    assert "4532-1234-5678-9012" not in cleaned
    assert "[REDACTED_CREDIT_CARD]" in cleaned

def test_detect_and_mask_ssn():
    firewall = PIIFirewall()
    text = "Employee SSN is 000-12-3456"
    cleaned, detected = firewall.redact(text)
    assert detected is True
    assert "000-12-3456" not in cleaned
    assert "[REDACTED_SSN]" in cleaned

def test_detect_api_keys():
    firewall = PIIFirewall()
    text = "Use key sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890"
    cleaned, detected = firewall.redact(text)
    assert detected is True
    assert "[REDACTED_SECRET]" in cleaned
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/unit/test_pii_firewall.py -v`
Expected: FAIL (PIIFirewall not defined)

- [ ] **Step 3: Implement `PIIFirewall` and integrate into `PolicyService`**

Implement `edith_x/modules/policy/firewall.py` using regex patterns for credit cards (with Luhn check), SSNs, emails, phone numbers, and cloud secrets (`sk-...`, `Bearer ...`). Integrate into `PolicyService.evaluate()` to enforce `requires_local=True` or payload masking.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/unit/test_pii_firewall.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add edith_x/modules/policy/ tests/unit/test_pii_firewall.py
git commit -m "feat(policy): implement enterprise PII and secret redaction firewall"
```

---

### Task 3: Resilient Multi-Provider Fallback Waterfall

**Files:**
- Modify: `edith_x/modules/execution/service.py`
- Test: `tests/unit/test_execution_waterfall.py`

- [ ] **Step 1: Write the failing unit tests for execution waterfall**

```python
# tests/unit/test_execution_waterfall.py
import pytest
from unittest.mock import AsyncMock, patch
from edith_x.core.config import Settings
from edith_x.core.interfaces import Context, ModelSelection
from edith_x.modules.execution.service import ExecutionService

@pytest.mark.asyncio
async def test_fallback_when_primary_provider_fails():
    settings = Settings(openai_api_key="test-key", nvidia_api_key="test-key")
    svc = ExecutionService(settings)
    ctx = Context(query="Summarize this text")
    primary_selection = ModelSelection(
        provider="nvidia_nim",
        model="meta/llama-3.1-70b-instruct",
        reasoning="Primary cloud model"
    )

    # Mock litellm: fail primary with 404, succeed fallback with 200
    with patch("litellm.acompletion") as mock_comp:
        from litellm.exceptions import NotFoundError
        mock_comp.side_effect = [
            NotFoundError(message="Model not found 404", model="nvidia_nim", llm_provider="nvidia_nim"),
            AsyncMock(
                choices=[{"message": {"content": "Fallback response from OpenAI"}}],
                usage={"prompt_tokens": 10, "completion_tokens": 15},
            )
        ]

        result = await svc.execute(ctx, primary_selection)
        assert result.response == "Fallback response from OpenAI"
        assert result.failover_active is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/unit/test_execution_waterfall.py -v`
Expected: FAIL (failover not implemented)

- [ ] **Step 3: Implement fallback waterfall in `ExecutionService`**

Implement automatic exception catching (`NotFoundError`, `AuthenticationError`, `RateLimitError`, `APIConnectionError`, `Timeout`) with automatic failover sequence to secondary cloud model or local model, setting `failover_active=True` and returning clean `ExecutionResult`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/unit/test_execution_waterfall.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add edith_x/modules/execution/service.py tests/unit/test_execution_waterfall.py
git commit -m "feat(execution): implement resilient multi-provider fallback waterfall"
```

---

### Task 4: Verifiable Cost Accounting & Prometheus Metrics

**Files:**
- Modify: `edith_x/modules/observability/service.py`
- Modify: `edith_x/interfaces/rest/app.py`
- Test: `tests/unit/test_observability_ledger.py`

- [ ] **Step 1: Write the failing unit tests for cost accounting**

```python
# tests/unit/test_observability_ledger.py
import pytest
from edith_x.core.config import Settings
from edith_x.core.interfaces import PipelineEvent
from edith_x.modules.observability.service import ObservabilityService

@pytest.mark.asyncio
async def test_cost_savings_calculation():
    obs = ObservabilityService(Settings())
    event = PipelineEvent(
        run_id="run-1",
        org_id="org-1",
        user_id="user-1",
        model_selected="llama-3.2-3b",
        provider="local_llm",
        cache_hit=False,
        tokens_input=1000,
        tokens_output=500,
        cost_usd=0.0,
        cost_saved_usd=0.0075, # (1000 * 2.50/1M) + (500 * 10.00/1M) - 0.0
        latency_ms=120,
        layer="L1_local"
    )
    await obs.record(event)
    assert obs.get_cumulative_savings() >= 0.0075
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/unit/test_observability_ledger.py -v`
Expected: FAIL

- [ ] **Step 3: Implement exact token ROI calculation and `/metrics` endpoint**

Update `ObservabilityService` with pricing lookup tables and expose Prometheus-compatible format at `/metrics`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/unit/test_observability_ledger.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add edith_x/modules/observability/ edith_x/interfaces/rest/app.py tests/unit/test_observability_ledger.py
git commit -m "feat(observability): add verifiable cost savings ledger and prometheus metrics"
```

---

### Task 5: End-to-End Integration Tests for Hybrid Gateway & Goal Engine

**Files:**
- Create: `tests/integration/test_hybrid_gateway.py`

- [ ] **Step 1: Write integration tests for OpenAI proxy and native Goal endpoint**

Test:
1. `POST /v1/chat/completions` with mock client (returns valid OpenAI schema with `usage`, `choices`, and `edith_metadata`).
2. `POST /edith/v1/run` multi-step LangGraph autonomous agent goal execution.
3. Verify cache hit on second identical request.

- [ ] **Step 2: Run all tests across the entire test suite**

Run: `.venv\Scripts\pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "test: add end-to-end integration tests for hybrid gateway"
```
