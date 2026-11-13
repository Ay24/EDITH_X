# Enterprise Resilience & Semantic Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement resilient enterprise circuit breakers, scalable two-tier bucketed vector caching, hybrid semantic centroid model routing, and timing-safe security hardening in EDITH-X.

**Architecture:** Combine fast-path heuristics with semantic centroid routing for model selection; upgrade semantic caching to coarse bucketed indexing with distributed L2 interfaces; guard upstream LLM calls with a 3-state jittered circuit breaker; and secure auth with timing-safe digest comparisons and non-blocking event-loop thread offloading.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, NumPy/math vectors, asyncio, hmac, pytest, structlog.

---

## File Structure

- **New files:**
  - `edith_x/modules/gateway/circuit_breaker.py`: Enterprise 3-state circuit breaker (`CLOSED`, `OPEN`, `HALF_OPEN`) with sliding window error rates, jitter, and canary recovery probes.
  - `tests/unit/test_circuit_breaker.py`: Unit tests for circuit breaker state transitions, timeout thresholds, and canary recovery.
  - `tests/unit/test_bucketed_cache.py`: Unit tests for two-tier caching, Voronoi cluster partitioning, and eviction.
  - `tests/unit/test_semantic_centroid_router.py`: Unit tests for centroid similarity evaluation on borderline routing queries.
  - `tests/unit/test_security_hardening.py`: Unit tests for `hmac.compare_digest` auth verification and sliding-window rate limiting.
- **Modified files:**
  - `edith_x/modules/identity/service.py`: Add `hmac.compare_digest` constant-time validation and sliding-window rate limiting.
  - `edith_x/modules/optimization/cache.py`: Add bucketed vector cluster partition and L2 distributed store interface.
  - `edith_x/modules/router/pareto.py`: Integrate semantic centroid cosine scoring for queries with intermediate complexity.
  - `edith_x/modules/gateway/service.py`: Integrate circuit breaker into provider dispatch and waterfall fallback.
  - `edith_x/modules/policy/firewall.py` & `edith_x/modules/optimization/compressor.py`: Use `asyncio.to_thread` for payloads $> 4\text{ KB}$.

---

## Tasks

### Phase 1: Security Hardening & Non-Blocking Loop Guard

- [ ] **Task 1.1**: Write unit tests for constant-time auth & sliding-window rate limiting (`tests/unit/test_security_hardening.py`)
  - Test timing-safe token validation (`hmac.compare_digest`).
  - Test sliding-window request limiter rejects bursts over tenant limits.
- [ ] **Task 1.2**: Implement constant-time auth & sliding-window limiter in `edith_x/modules/identity/service.py`
  - Update `validate_api_key` to use `hmac.compare_digest`.
  - Add in-memory sliding-window bucket to verify requests per minute per tenant.
  - Run `pytest tests/unit/test_security_hardening.py` to verify pass.
- [ ] **Task 1.3**: Add `asyncio.to_thread` offloading for large payloads in `firewall.py` & `compressor.py`
  - Wrap regex and entropy scans in `asyncio.to_thread` when input length $> 4,096$ chars.
  - Run `pytest tests/unit/test_pii_firewall.py tests/unit/test_context_optimizer.py`.
- [ ] **Task 1.4**: Commit Phase 1 changes to git.

---

### Phase 2: 3-State Resilient Circuit Breaker

- [ ] **Task 2.1**: Write unit tests for circuit breaker in `tests/unit/test_circuit_breaker.py`
  - Test normal operations in `CLOSED` state.
  - Test transition to `OPEN` when error rate $\ge 50\%$ or consecutive timeouts occur.
  - Test fast-fail when `OPEN` without calling provider.
  - Test transition to `HALF_OPEN` after recovery cooldown and probe handling.
- [ ] **Task 2.2**: Implement `CircuitBreaker` in `edith_x/modules/gateway/circuit_breaker.py`
  - Define `CircuitState` (`CLOSED`, `OPEN`, `HALF_OPEN`).
  - Implement rolling failure window, exponential backoff with random jitter, and canary probe counts.
- [ ] **Task 2.3**: Integrate `CircuitBreaker` into `GatewayService` / `ExecutionService`
  - Wire circuit breaker checks into provider execution waterfall in `edith_x/modules/gateway/service.py`.
  - Run `pytest tests/unit/test_circuit_breaker.py` and `pytest tests/unit/test_gateway_service.py`.
- [ ] **Task 2.4**: Commit Phase 2 changes to git.

---

### Phase 3: Bucketed Vector Index & Two-Tier Caching

- [ ] **Task 3.1**: Write unit tests for bucketed vector caching in `tests/unit/test_bucketed_cache.py`
  - Test partition cluster assignment based on normalized vector dimensions.
  - Test sub-millisecond retrieval of semantic entries from bucketed index.
  - Test two-tier L1 memory and L2 distributed adapter fallback.
- [ ] **Task 3.2**: Implement bucketed vector indexing in `edith_x/modules/optimization/cache.py`
  - Add coarse Voronoi partition hashing for vector embeddings ($K$ buckets).
  - Search matching bucket and adjacent cluster partitions instead of entire array.
  - Maintain L1 LRU memory store and L2 interface protocol.
  - Run `pytest tests/unit/test_bucketed_cache.py`.
- [ ] **Task 3.3**: Commit Phase 3 changes to git.

---

### Phase 4: Hybrid Semantic Centroid Model Routing

- [ ] **Task 4.1**: Write unit tests for semantic centroid routing in `tests/unit/test_semantic_centroid_router.py`
  - Test fast-path bypass for queries with unambiguous simple/complex heuristics.
  - Test centroid cosine calculation for ambiguous queries ($0.35 \le c \le 0.70$).
  - Test cost/budget threshold shifting based on tenant tier.
- [ ] **Task 4.2**: Implement centroid semantic evaluation in `edith_x/modules/router/pareto.py`
  - Define normalized reference centroids for complex reasoning vs simple knowledge queries.
  - When complexity falls in borderline band ($0.35$ to $0.70$), compute cosine similarity with centroids to decide tier.
  - Run `pytest tests/unit/test_semantic_centroid_router.py` and `pytest tests/unit/test_router.py`.
- [ ] **Task 4.3**: Commit Phase 4 changes to git.

---

### Phase 5: End-to-End Regression & Benchmark Verification

- [ ] **Task 5.1**: Run full project test suite
  - Run `pytest` to verify all 63 existing tests + 4 new test suites pass with 0 errors.
- [ ] **Task 5.2**: Run benchmark suite
  - Run `pytest tests/benchmarks/` to verify latency and accuracy comply with `thresholds.yaml`.
- [ ] **Task 5.3**: Commit all changes and push to `origin/master`.
