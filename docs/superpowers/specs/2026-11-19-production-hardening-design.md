# EDITH-X Production Hardening & Architectural Security Design Spec
**Approach B: Comprehensive Production Hardening (Zero External Dependencies)**

- **Date**: 2026-11-19
- **Author**: Lead Architect & AI Security Engineer
- **Status**: Approved for Implementation
- **Target Release**: EDITH-X v0.1.1 Production Hardened

---

## 1. Problem Statement & Scope

During the zero-bias production load and reliability testing suite (`tests/prod_sim`), five critical defects and architectural bottlenecks were identified:
1. **BUG-001 (CRITICAL P0 - Auth Bypass)**: `GatewayService.authenticate()` line 50 returns `_DEMO_AUTH` for any forged bearer token instead of rejecting with HTTP 401 Unauthorized.
2. **BUG-002 (HIGH P1 - Data Leakage)**: Endpoints `/edith/v1/run` and `/v1/chat/completions` bypass `EnterprisePIIFirewall.sanitize()`, forwarding raw card numbers and secrets to upstream LLM providers.
3. **BUG-003 (CRITICAL P0 - Cross-Tenant Retrieval)**: `PlannerService._node_retrieve()` calls `knowledge.retrieve()` without passing `org_id`, leaking private documents across organizations.
4. **BUG-004 (CRITICAL P0 - Shared Semantic Cache)**: `SemanticCache` keys are generated without `org_id` namespacing, serving cached answers across different tenant boundaries.
5. **BUG-005 (MEDIUM P2 - Memory Leak in Rate Limiter)**: `GatewayService._request_timestamps` in-memory dictionary grows without bounding or TTL eviction of inactive keys.

---

## 2. Architectural Design & Component Specifications

### 2.1 Module 1: Gateway & Authentication Hardening (`edith_x/modules/gateway/service.py`)

#### A. Timing-Safe & Structured Authentication
- **Zero-Dependency Cryptography**: Utilize Python standard library `hmac`, `secrets`, `hashlib`, plus existing `python-jose` for JWT validation.
- **Strict Verification Protocol**:
  1. Extract bearer token from `Authorization` header.
  2. If token matches configured API keys (`settings.api_key`, or recognized tenant patterns `edx_live_admin_<org>` / `edx_live_user_<org>`): validate in constant time (`hmac.compare_digest`) and bind to the correct `AuthContext` with appropriate `role` and `org_id`.
  3. If token is a JWT: decode using `jose.jwt` with configured secret and algorithm; verify expiration and signature.
  4. If `demo_mode=True` and token == `"demo-key"`: map to designated demo tenant.
  5. **FAIL-CLOSED POLICY**: Any forged, invalid, expired, or unrecognized key returns `None`. In `get_auth()`, returning `None` immediately raises `HTTPException(status_code=401, detail="Invalid or forged API credentials")`.

#### B. Bounded LRU Sliding Window Rate Limiter
- Replace the unbounded `dict[str, list[float]]` with an active bounded tracker:
  - Add active cleanup that evicts timestamps older than `window_seconds`.
  - Cap maximum tracked keys (e.g. 10,000 active clients). Evict stale entries using `collections.OrderedDict` LRU behavior to guarantee memory bounds.

---

### 2.2 Module 4: Live PII & Secret Redaction Wiring (`edith_x/interfaces/rest/app.py` & `service.py`)

#### Redaction Protocol
- In `/edith/v1/run` and `/v1/chat/completions`:
  1. Instantiate or inject `EnterprisePIIFirewall`.
  2. Call `redacted_prompt, matches = firewall.sanitize(prompt_text)`.
  3. If `matches` contain high-entropy private keys or unmasked card numbers:
     - Log a structured security alert: `event="pii_intercepted", tenant=auth.org_id, match_types=[m.pattern_type for m in matches]`.
     - Replace the raw prompt in the execution state with `redacted_prompt`.
  4. Upstream model calls and downstream retrieval operations strictly receive the sanitized prompt.

---

### 2.3 Module 5 & 6: Tenant-Partitioned Knowledge Retrieval (`planner/service.py` & `knowledge/service.py`)

#### Secure Context Retrieval
- In `PlannerService._node_retrieve()`:
  - Extract `auth: AuthContext = state.get("auth")`.
  - Pass `org_id=auth.org_id` explicitly to `self._knowledge.retrieve(goal, org_id=auth.org_id, top_k=5)`.
- In `KnowledgeService.retrieve()`:
  - Construct a strict Qdrant filter condition:
    ```python
    Filter(
        must=[
            FieldCondition(
                key="metadata.org_id",
                match=MatchValue(value=org_id)
            )
        ]
    )
    ```
  - Disallow vector retrieval without an explicit `org_id`. Cross-tenant search queries return zero documents.

---

### 2.4 Module 8: Tenant-Namespaced Semantic Cache (`optimization/cache.py` & `cache/semantic.py`)

#### Namespaced Cache Partitioning
- Update cache hashing and indexing:
  ```python
  # All cache keys prefixed with tenant context
  cache_key = f"{org_id}:{query_hash}"
  ```
- In `SemanticCache.get()`:
  - Only compute similarity against queries stored under the identical `org_id`.
  - Under no circumstance can a cache hit return a response stored by a different `org_id`.

---

### 2.5 Module 2 & 14: Tamper-Evident Audit Logging (`identity/service.py`)

- Implement `AuditLedgerService` using standard library `hashlib` (SHA-256):
  - Every sensitive event (auth success/failure, policy block, tool invocation) generates an audit entry:
    ```json
    {
      "timestamp": 1795099800.12,
      "event": "run_goal",
      "org_id": "org_01",
      "user_id": "usr_42",
      "prev_hash": "a1b2...",
      "entry_hash": "c3d4..."
    }
    ```
  - Appends to an append-only JSONL log with hash chaining to ensure non-repudiation (SOC2 CC6.1).

---

## 3. Data Flow Diagram

```mermaid
flowchart TD
    Client["Client Request<br/>(Bearer Token)"] -->|1. HTTP Header| GW["GatewayService<br/>Timing-Safe Auth"]
    GW -->|Invalid Token| R401["HTTP 401 Unauthorized<br/>(Fail Closed)"]
    GW -->|Valid Token| AuthCtx["AuthContext<br/>(org_id, role, user_id)"]
    
    AuthCtx --> PII["EnterprisePIIFirewall<br/>Sanitize Raw Prompt"]
    PII -->|Redacted Text| SC["SemanticCache<br/>Partitioned by org_id"]
    
    SC -->|Cache Hit (Same Org)| Response["HTTP 200 Cached Result"]
    SC -->|Cache Miss| Planner["Planner Graph<br/>State carries AuthContext"]
    
    Planner --> Retrieve["KnowledgeService<br/>Filter: metadata.org_id == caller.org_id"]
    Retrieve --> Router["Pareto Cost Router"]
    Router --> Model["Upstream LLM Provider"]
    Model --> Audit["Audit Ledger<br/>SHA-256 Hash Chained"]
    Audit --> ResponseLive["HTTP 200 Live Response"]
```

---

## 4. Verification Plan

1. **Unit & Regression Tests**:
   - `test_auth_rejects_forged_tokens()`: verify HTTP 401 on random/forged tokens.
   - `test_pii_sanitization_in_run()`: verify raw credit card numbers are replaced with `[REDACTED_CREDIT_CARD]` before LLM dispatch.
   - `test_cross_tenant_isolation()`: verify Org A cannot retrieve Org B canary strings.
   - `test_cache_tenant_partitioning()`: verify Org B does not get cache hit on Org A query.
   - `test_rate_limiter_memory_bounds()`: verify key eviction on 10,000+ simulated users.
2. **Production Simulation Re-run**:
   - Run `tests/prod_sim/run_prod_sim.py` and confirm T7 Isolation & Security Audit turns **PASS**.
