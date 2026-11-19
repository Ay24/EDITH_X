# EDITH-X Production Defects Log (BUGS.md)

**Status Summary**: All identified defects (BUG-001 through BUG-005) have been systematically resolved and verified with dedicated regression tests. Zero external dependencies were introduced.

---

### BUG-001: Authentication Fallback Grants Full Admin Access to Forged API Keys
- **File**: [`edith_x/modules/gateway/service.py`](file:///c:/Users/Abhay/Downloads/Ai_hakcathon\EDITH-Enterprise\edith-x\edith_x\modules\gateway\service.py), [`edith_x/interfaces/rest/app.py`](file:///c:/Users/Abhay/Downloads/Ai_hakcathon\EDITH-Enterprise\edith-x\edith_x\interfaces\rest\app.py)
- **Severity**: **CRITICAL (P0 - Security)**
- **Status**: **RESOLVED & VERIFIED** (Tested via unit test and real HTTP live probe)
- **Fix Details**:
  - Removed insecure `return _DEMO_AUTH` fall-through in `GatewayService.authenticate()`.
  - Implemented timing-safe verification for recognized keys (`demo-key`, static configured key, and structured enterprise keys `edx_live_{role}_{org_id}`).
  - Implemented fail-closed security: Any unrecognized, forged, or empty key returns `None`.
  - In `app.py:get_auth()`, returning `None` immediately raises `HTTPException(status_code=401, detail="Invalid, expired, or forged API credentials.")`.
- **Verification**:
  - `curl -i -X GET http://127.0.0.1:8000/edith/v1/metrics -H "Authorization: Bearer forged-evil-token"` -> **HTTP/1.1 401 Unauthorized**.

---

### BUG-002: Prompt PII & Secrets Are Not Redacted in Live Execution Endpoints
- **File**: [`edith_x/interfaces/rest/app.py`](file:///c:/Users/Abhay/Downloads/Ai_hakcathon\EDITH-Enterprise\edith-x\edith_x\interfaces\rest\app.py)
- **Severity**: **HIGH (P1 - Compliance / Data Protection)**
- **Status**: **RESOLVED & VERIFIED** (Verified in `tests/test_pii_live_firewall.py`)
- **Fix Details**:
  - Wired `policy_svc.sanitize_payload()` into `/edith/v1/run` and `/v1/chat/completions`.
  - The raw user goal is sanitized before being passed to `planner.run()` and upstream LLMs.
  - Credit card numbers, SSNs, and high-entropy secret tokens are masked with `[REDACTED_CREDIT_CARD]`, `[REDACTED_SSN]`, etc.
- **Verification**:
  - Tests verify that inputs containing Luhn-valid card numbers and API keys are redacted before dispatch to upstream model providers.

---

### BUG-003: Cross-Tenant Knowledge Retrieval Leakage in Planner Graph
- **File**: [`edith_x/modules/planner/service.py`](file:///c:/Users/Abhay/Downloads/Ai_hakcathon\EDITH-Enterprise\edith-x\edith_x\modules\planner\service.py#L55-L65)
- **Severity**: **CRITICAL (P0 - Multi-Tenancy)**
- **Status**: **RESOLVED & VERIFIED** (Verified in `tests/test_tenant_knowledge_isolation.py`)
- **Fix Details**:
  - Extracted `org_id` from `state["auth"].org_id` in `PlannerService._node_retrieve()`.
  - Passed `org_id=org_id` into `self._knowledge.retrieve(goal, sources=[], top_k=5, org_id=org_id)`.
  - Qdrant queries now strictly enforce payload filtering on `FieldCondition(key="org_id", match=MatchValue(value=org_id))`.
- **Verification**:
  - Tests confirm that Tenant B cannot retrieve Tenant A's documents or canaries even when explicitly querying for them.

---

### BUG-004: Semantic Cache Cross-Tenant Data Poisoning
- **File**: [`edith_x/modules/optimization/cache.py`](file:///c:/Users/Abhay/Downloads/Ai_hakcathon\EDITH-Enterprise\edith-x\edith_x\modules\optimization\cache.py), [`edith_x/modules/optimization/service.py`](file:///c:/Users/Abhay/Downloads/Ai_hakcathon\EDITH-Enterprise\edith-x\edith_x\modules\optimization\service.py), [`edith_x/modules/planner/service.py`](file:///c:/Users/Abhay/Downloads/Ai_hakcathon\EDITH-Enterprise\edith-x\edith_x\modules\planner\service.py)
- **Severity**: **CRITICAL (P0 - Multi-Tenancy)**
- **Status**: **RESOLVED & VERIFIED** (Verified in `tests/test_cache_tenant_partitioning.py`)
- **Fix Details**:
  - Added `org_id` to `CacheEntry`.
  - Namespaced SHA-256 hash keys by tenant: `hashlib.sha256(f"{org_id}:{_normalize(query)}".encode())`.
  - In semantic vector similarity search, filtered candidate matches to only entries matching `entry.org_id == org_id`.
  - Updated `OptimizationService.check_cache()`, `OptimizationService.store_cache()`, and `PlannerService` to thread `org_id`.
- **Verification**:
  - Tests confirm identical queries from different tenants produce cache misses for cross-tenant probes while hitting for the owning tenant.

---

### BUG-005: Unbounded In-Memory Rate Limiter Memory Growth Under Concurrent Load
- **File**: [`edith_x/modules/gateway/service.py`](file:///c:/Users/Abhay/Downloads/Ai_hakcathon\EDITH-Enterprise\edith-x\edith_x\modules\gateway\service.py)
- **Severity**: **MEDIUM (P2 - Reliability)**
- **Status**: **RESOLVED & VERIFIED** (Verified in `tests/test_gateway_security.py`)
- **Fix Details**:
  - Replaced plain `dict` with bounded `OrderedDict` (capped at 10,000 active clients).
  - Implemented automatic key eviction (`popitem(last=False)`) when reaching capacity.
  - Implemented automatic stale key removal when timestamp lists expire.
  - Added `prune_stale_clients(max_age_seconds)` maintenance method.
- **Verification**:
  - Tests simulate 500 transient callers and verify that calling `prune_stale_clients` completely reclaims memory without residue.
