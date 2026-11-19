# EDITH-X Architectural Reconnaissance & Honest Gap Analysis

**Author**: Senior Performance & Reliability Engineering  
**Date**: November 19, 2026  
**Target Environment**: Windows 11 (AMD Ryzen 5 5600H, 16 GB RAM, Python 3.11.0)  
**Scope**: Complete static & runtime audit of `edith_x/`, `docker-compose.yml`, `Dockerfile`, `.env`, and existing test suites.

---

## 1. Executive Summary & Security Notice

> [!WARNING]
> **Secret Exposure in `.env` (Rule 7 Check)**:
> An inspection of `.env` revealed a live API key (`NVIDIA_API_KEY=nvapi-...`). Per Rule 7, this secret will NOT be used or printed in any load test artifact. All load testing will execute against an isolated local mock or dummy keys (`edx_test_...`, `demo-key`).

EDITH-X is an ambitious, modular enterprise AI gateway providing caching, routing, tool sandboxing, and policy enforcement. However, a rigorous code review across modules M1–M14 uncovers critical architectural contradictions between design claims and actual code execution paths.

---

## 2. Module-by-Module Reality Assessment

| Module | Purpose | Status | Real Implementation vs Stubbed / Mocked Reality |
| :--- | :--- | :--- | :--- |
| **M1: Gateway** (`gateway/service.py`) | Auth & Rate Limiting | **Partially Implemented** | **Critical Security Flaw**: In `authenticate()`, if `validate_key_timing_safe` fails or key is unknown, line 50 unconditionally returns `_DEMO_AUTH` (`org_id='demo-org-001'`, `role='admin'`). Any random or forged key gets full admin access! Rate limiter uses an in-memory dictionary of timestamps. |
| **M2: Identity** (`identity/service.py`) | Tenant RBAC & Auth | **Partially Implemented** | Keys starting with `edx_live_<org>_<token>` or `edx_test_<org>_<token>` are parsed via string split (`parts[2]`). There is **no database backing**, no asymmetric JWT cryptographic verification, and no revocation list. |
| **M3: Intent** (`intent/service.py`) | Query Classification | **Implemented** | Uses `CentroidIntentRouter` with TF-IDF cosine similarity across 9 intent vectors, plus keyword checks for complexity. Runs in < 1 ms on CPU. |
| **M4: Policy / PII** (`policy/service.py`, `policy/firewall.py`) | PII / Secret Firewall | **Disconnected from Main Pipeline** | `PIIFirewall` implements regex for cards, SSNs, emails, phone numbers, and Shannon entropy. **CRITICAL DEFECT**: Neither `/v1/chat/completions` nor `/edith/v1/run` calls `firewall.redact()` on user queries! The firewall is only exposed on `/edith/v1/policy/scan`. In production requests, raw prompts pass unredacted. |
| **M5: Planner** (`planner/service.py`) | Autonomous Execution | **Partially Implemented** | Uses LangGraph `StateGraph`. However, in `_node_retrieve` (line 61), it calls `self._knowledge.retrieve(goal, sources=[], top_k=5)` **without passing `org_id`**! Every user query searches the shared global collection without tenant filtering. |
| **M6: Knowledge** (`knowledge/service.py`) | Qdrant Hybrid RAG | **Implemented (with Leaks)** | Dense pseudo-semantic hashing (128-dim) + lexical BM25 fallback. Supports `org_id` filtering in `retrieve()`, but `app.py` (`/edith/v1/knowledge/query`) and `planner/service.py` omit `org_id`, enabling complete cross-tenant document exposure. |
| **M8: Cache** (`optimization/cache.py`) | L0 Exact & Semantic Cache | **Implemented (Single-Tenant Only)** | Two-tier LRU cache (SHA-256 exact + cosine semantic vector lookup). **CRITICAL DEFECT**: The cache has **no `org_id` partitioning**. Cache keys are derived strictly from prompt text. If Tenant A caches an internal financial answer, Tenant B asking the same question receives Tenant A's cached response! |
| **M9: Router** (`router/pareto.py`) | Cost-Complexity Routing | **Implemented** | Heuristic formula based on prompt length, code fences, and keyword presence (proof, consensus, byzantine). Output is deterministic and fast (< 0.2 ms). |
| **M10: Execution** (`execution/service.py`) | LiteLLM LLM Dispatch | **Implemented** | LiteLLM wrapper with circuit breaker and fallback waterfall (`nvidia_nim` -> `groq` -> `openai` -> `anthropic` -> `local_llm`). |
| **M13: Memory** (`memory/service.py`) | Mem0 Conversation Memory | **Stubbed Fallback** | `mem0` library is not installed in the environment; falls back to an in-memory dictionary `self._fallback_store: dict[str, list[dict]]`. Data is lost on process restart. |
| **M14: Observability** (`observability/service.py`) | Metrics & Telemetry | **Implemented (In-Memory)** | In-memory ledger storing events. Provides Prometheus text formatter `/metrics` and `/edith/v1/metrics`. Not backed by persistent Prometheus or OpenTelemetry collector. |

---

## 3. Endpoints Inventory

| Method | Path | Auth Required | True Functionality |
| :--- | :--- | :--- | :--- |
| `GET` | `/` and `/dashboard` | No | Serves static HTML/JS dashboard from `static/index.html`. |
| `GET` | `/edith/v1/health` | No | Returns JSON status and provider key presence flags. |
| `POST` | `/v1/chat/completions` | Yes (Header) | OpenAI-compatible chat completions; runs LangGraph planner. Streams word-by-word via sleep(0.02) if stream=True. |
| `POST` | `/edith/v1/run` | Yes (Header) | Native goal execution; runs LangGraph planner; returns cost & cache metrics. |
| `GET` | `/edith/v1/metrics` | Yes (Header) | Returns in-memory metrics, cumulative cost, and recent events. |
| `POST` | `/edith/v1/documents` | Yes (Header) | Upserts document into Qdrant collection. Uses `request.metadata['org_id']`. |
| `GET` | `/edith/v1/memory` | Yes (Header) | Retrieves user memories from in-memory fallback dict. |
| `GET` | `/metrics` | No | Returns Prometheus standard exposition format text. |
| `POST` | `/edith/v1/policy/scan` | Yes (Header) | Dedicated PII redaction and Shannon entropy scanner. |
| `GET` | `/edith/v1/knowledge/query` | Yes (Header) | Queries Qdrant without `org_id` filter (cross-tenant leak). |

---

## 4. Evaluation of Existing Test Suites

- **Circular / Trivial Tests**:
  - `tests/unit/test_pareto_router.py`: Evaluates queries hand-crafted with keywords ("proof", "byzantine") matching the router's internal keyword list.
  - `tests/benchmarks/runners/test_routellm_pareto.py`: Evaluated in-process without calling a real or mock LLM.
  - `tests/benchmarks/runners/test_gateway_latency.py`: Measures in-process CPU loops (`asyncio.gather` over synchronous regex), not real HTTP network hop or socket serialization.
- **Genuine & Rigorous Tests**:
  - `tests/unit/test_semantic_cache_polarity.py`: Accurately tests semantic cache polarity flips ("with" vs "without").
  - `tests/unit/test_tool_registry.py`: Tests AST arithmetic evaluator against dangerous expressions (`__import__`, `eval`).
  - `tests/unit/test_circuit_breaker.py`: Accurately tests state machine transitions (`CLOSED` -> `OPEN` -> `HALF_OPEN`).

---

## 5. Reconnaissance Conclusion for Prod-Sim

To perform a genuine stress and reliability test:
1. We cannot rely on in-process module calls. Everything must hit the running REST API over **real HTTP loopback sockets** (`http://127.0.0.1:8000`).
2. We must build a **Mock LLM service** that speaks the OpenAI API with realistic lognormal latency and configurable fault injection (timeouts, 429s, 500s).
3. We must test the actual cross-tenant isolation and canary leaks, specifically exploiting the missing `org_id` in `PlannerService` and `SemanticCache`.
