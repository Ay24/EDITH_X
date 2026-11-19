# EDITH-X Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permanently resolve all critical security, multi-tenancy, compliance, and memory defects (BUG-001 through BUG-005) identified in testing without introducing new external dependencies.

**Architecture:** Timing-safe authentication and fail-closed key validation in `GatewayService`, pre-execution PII/secret redaction in FastAPI route handlers, tenant-partitioned vector retrieval in `PlannerService`/`KnowledgeService`, tenant-namespaced exact and semantic caching in `SemanticCache`, and bounded LRU eviction in rate limiting.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Python stdlib (`hmac`, `hashlib`, `secrets`, `collections`), Qdrant Client. Zero new dependencies.

---

### Task 1: Fix BUG-001 (Fail-Closed Auth) & BUG-005 (Bounded Rate Limiter)

**Files:**
- Modify: `edith_x/modules/gateway/service.py`
- Modify: `edith_x/interfaces/rest/app.py`
- Test: `tests/test_gateway_security.py`

- [ ] **Step 1: Write unit test verifying forged tokens return 401 and valid demo/live tokens work**
- [ ] **Step 2: Update `GatewayService.authenticate()` to eliminate `return _DEMO_AUTH` fall-through**
- [ ] **Step 3: Update `GatewayService._request_timestamps` to bounded LRU sliding window with periodic stale key cleanup**
- [ ] **Step 4: Run tests to verify pass**

---

### Task 2: Fix BUG-002 (Wire EnterprisePIIFirewall into Live Execution)

**Files:**
- Modify: `edith_x/interfaces/rest/app.py`
- Modify: `edith_x/modules/planner/service.py`
- Test: `tests/test_pii_live_firewall.py`

- [ ] **Step 1: Write test verifying credit card numbers and secrets are redacted in `/edith/v1/run`**
- [ ] **Step 2: Wire `EnterprisePIIFirewall.sanitize()` into `/edith/v1/run` and `/v1/chat/completions`**
- [ ] **Step 3: Replace raw user prompt with sanitized text before passing to planner and upstream models**
- [ ] **Step 4: Run test to verify pass**

---

### Task 3: Fix BUG-003 (Tenant-Partitioned Knowledge Retrieval)

**Files:**
- Modify: `edith_x/modules/planner/service.py`
- Modify: `edith_x/modules/knowledge/service.py`
- Test: `tests/test_tenant_knowledge_isolation.py`

- [ ] **Step 1: Write test verifying Tenant A cannot retrieve Tenant B's documents in planner graph**
- [ ] **Step 2: Update `PlannerService._node_retrieve()` to pass `org_id=state["auth"].org_id`**
- [ ] **Step 3: Update `KnowledgeService.retrieve()` to enforce Qdrant filter on `metadata.org_id`**
- [ ] **Step 4: Run test to verify pass**

---

### Task 4: Fix BUG-004 (Tenant-Namespaced Semantic Cache)

**Files:**
- Modify: `edith_x/modules/cache/semantic.py`
- Modify: `edith_x/modules/optimization/cache.py`
- Test: `tests/test_cache_tenant_partitioning.py`

- [ ] **Step 1: Write test verifying identical query from Org A and Org B creates separate cache entries**
- [ ] **Step 2: Prefix all cache keys and semantic lookup indices with `org_id`**
- [ ] **Step 3: Filter semantic cosine candidates strictly by caller's `org_id`**
- [ ] **Step 4: Run test to verify pass**

---

### Task 5: Add Tamper-Evident Hash-Chained Audit Ledger

**Files:**
- Create: `edith_x/modules/identity/audit_ledger.py`
- Modify: `edith_x/modules/identity/service.py`
- Test: `tests/test_audit_ledger.py`

- [ ] **Step 1: Implement `AuditLedger` with SHA-256 hash chaining using Python stdlib `hashlib`**
- [ ] **Step 2: Hook audit event recording into `IdentityService.log_audit()` and gateway execution**
- [ ] **Step 3: Run test verifying chain integrity verification**

---

### Task 6: Re-Execute Production Simulation Suite (T0 to T8 Verification)

**Files:**
- Run: `tests/prod_sim/run_prod_sim.py`
- Verify: `tests/prod_sim/REPORT.md`

- [ ] **Step 1: Restart `edith-api` with hardened codebase**
- [ ] **Step 2: Run `python -u tests/prod_sim/run_prod_sim.py`**
- [ ] **Step 3: Verify T7 Isolation & Security passes with 0 leaks, 0 forged auth bypasses, and 100% PII recall**
