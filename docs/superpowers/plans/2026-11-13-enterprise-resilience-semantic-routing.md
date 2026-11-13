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

- [x] **Task 1.1**: Write unit tests for constant-time auth & sliding-window rate limiting (`tests/unit/test_security_hardening.py`)
- [x] **Task 1.2**: Implement constant-time auth & sliding-window limiter in `edith_x/modules/identity/service.py`
- [x] **Task 1.3**: Add `asyncio.to_thread` offloading for large payloads in `firewall.py` & `compressor.py`
- [x] **Task 1.4**: Commit Phase 1 changes to git.

---

### Phase 2: 3-State Resilient Circuit Breaker

- [x] **Task 2.1**: Write unit tests for circuit breaker in `tests/unit/test_circuit_breaker.py`
- [x] **Task 2.2**: Implement `CircuitBreaker` in `edith_x/modules/gateway/circuit_breaker.py`
- [x] **Task 2.3**: Integrate `CircuitBreaker` into `GatewayService` / `ExecutionService`
- [x] **Task 2.4**: Commit Phase 2 changes to git.

---

### Phase 3: Bucketed Vector Index & Two-Tier Caching

- [x] **Task 3.1**: Write unit tests for bucketed vector caching in `tests/unit/test_bucketed_cache.py`
- [x] **Task 3.2**: Implement bucketed vector indexing in `edith_x/modules/optimization/cache.py`
- [x] **Task 3.3**: Commit Phase 3 changes to git.

---

### Phase 4: Hybrid Semantic Centroid Model Routing

- [x] **Task 4.1**: Write unit tests for semantic centroid routing in `tests/unit/test_semantic_centroid_router.py`
- [x] **Task 4.2**: Implement centroid semantic evaluation in `edith_x/modules/router/pareto.py`
- [x] **Task 4.3**: Commit Phase 4 changes to git.

---

### Phase 5: End-to-End Regression & Benchmark Verification

- [x] **Task 5.1**: Run full project test suite (76 of 76 tests passing)
- [x] **Task 5.2**: Run benchmark suite (meets all pre-committed thresholds in thresholds.yaml)
- [x] **Task 5.3**: Commit all changes and push to `origin/master`.
