# EDITH-X Enterprise AI Runtime: Production Hardening Design

**Date**: 2026-11-12  
**Status**: Approved  
**Integration Type**: Hybrid (OpenAI Drop-In Proxy + Autonomous Agent Runtime)  

---

## 1. Executive Summary & Value Proposition

EDITH-X is an enterprise AI runtime deployed as an internal orchestration layer between corporate applications and AI models. It solves three critical enterprise adoption barriers:
1. **Zero-Friction Drop-In**: 100% OpenAI API compatible (`/v1/chat/completions`) with zero client code rewrite.
2. **Hard Token Cost Reduction (60–80%)**: Enforces a 4-layer cost firewall (L0 Semantic Cache, L1 Local Edge, L2 Compressed Cloud, L3 Frontier Cloud) with verifiable ROI auditing.
3. **High Reliability & Zero 500s**: A resilient, self-healing multi-provider fallback waterfall that automatically reroutes around quota limits, timeouts, and rate limits without breaking client applications.
4. **Data Sovereignty & PII Firewall**: Automatic detection and redaction of PII and enterprise secrets, routing sensitive payloads to local air-gapped models.

---

## 2. System Architecture

```
Client App (OpenAI SDK / HTTP) ───┐
                                  ├──> [FastAPI REST Gateway]
Autonomous Agent (/edith/v1/run) ─┘              │
                                                 ▼
                                     [Auth & Rate Limiting]
                                                 │
                                                 ▼
                                  [Policy & PII Redaction Firewall]
                                     │                        │
                          (PII Detected)                (Clean Payload)
                                     ▼                        ▼
                          [Force L1 Local Ollama]    [Intent & Complexity Router]
                                                              │
                                                              ▼
                                                   [L0 Semantic Cache]
                                                    │               │
                                              (Cache Hit)      (Cache Miss)
                                                    │               │
                                                    ▼               ▼
                                            [Return <25ms]     [Model Router Waterfall]
                                                               [L1 Local -> L2 NIM -> L3 Frontier]
                                                                    │
                                                                    ▼
                                                       [Circuit Breaker / Fallback]
                                                                    │
                                                                    ▼
                                                       [Verifiable Savings Ledger]
```

---

## 3. Detailed Component Specifications

### 3.1 M8 Optimization Layer: Dual Semantic Cache
- **Exact-Match Cache**: Fast cryptographic hash (SHA-256) of normalized prompt. Lookup latency: `< 2ms`.
- **Semantic Cache**: In-memory and vector-backed cosine similarity comparison using lightweight embeddings (`all-MiniLM-L6-v2` or local hash embeddings).
  - Cosine threshold: $\ge 0.92$ triggers cache hit.
  - Return payload: Cached text, token savings calculation against GPT-4o baseline, latency $\le 20\text{ms}$.
- **Storage**: In-memory LRU cache with optional Qdrant vector backend.

### 3.2 M10 Execution Engine: Resilient Fallback Waterfall
- **Primary Route Selection**: Derived from `IntentResult` and `PolicyDecision`.
- **Waterfall Sequence**:
  - Target: Primary Model (e.g. NVIDIA NIM Llama 3.1 70B, Ollama 8B, or GPT-4o).
  - Primary Exception Catch: HTTP 401, 404, 429, 500, ConnectionError, Timeout.
  - Automatic Cascading:
    1. Try Primary Model.
    2. If failure $\rightarrow$ log structured warning, trip circuit breaker.
    3. Cascade to Secondary Model (e.g., Fast Cloud / OpenAI GPT-4o-mini / Groq).
    4. If failure $\rightarrow$ Cascade to Local L1 Model (Ollama/vLLM).
    5. Return graceful response with status indicator (`"failover_active": true`).

### 3.3 M4 Policy Layer: PII & Token Firewall
- Scans user prompts for sensitive data patterns:
  - Credit Cards (Luhn validation regex)
  - Social Security Numbers (SSN)
  - API Keys / Bearer tokens
  - Email addresses & Phone numbers
- Policy Enforcement:
  - Action `mask`: Replaces matching spans with `[REDACTED_<TYPE>]` before cloud transmission.
  - Action `route_local`: Automatically overrides routing decision to `L1_local` to prevent data exfiltration.

### 3.4 M14 Observability: Verifiable Cost Ledger
- Mathematical formula:
  $$\text{Baseline Cost} = (\text{Tokens}_{\text{in}} \times \$2.50 / 10^6) + (\text{Tokens}_{\text{out}} \times \$10.00 / 10^6)$$
  $$\text{Actual Cost} = (\text{Tokens}_{\text{in}} \times P_{\text{model\_in}}) + (\text{Tokens}_{\text{out}} \times P_{\text{model\_out}})$$
  $$\text{Dollars Saved} = \text{Baseline Cost} - \text{Actual Cost}$$
- Exposes Prometheus-compatible `/metrics` and JSON `/edith/v1/metrics`.

---

## 4. Test Strategy

1. **Unit Tests**:
   - `test_semantic_cache.py`: Exact hash hit, semantic similarity hit, threshold misses.
   - `test_pii_firewall.py`: Regex matching, token masking, policy override.
   - `test_execution_waterfall.py`: Mocking upstream 404/429/500 errors and verifying automatic cascade.
   - `test_cost_ledger.py`: Token calculation and savings accounting.
2. **Integration Tests**:
   - `test_openai_dropin.py`: End-to-end `/v1/chat/completions` request/response flow.
   - `test_goal_runner.py`: End-to-end `/edith/v1/run` multi-step LangGraph graph.
