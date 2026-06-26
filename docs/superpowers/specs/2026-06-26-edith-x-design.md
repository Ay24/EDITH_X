# EDITH-X Enterprise AI Runtime — Design Specification v1.0
**Date:** 2026-06-26 | **Status:** Pending User Approval

---

## 1. Vision

EDITH-X is an **Enterprise AI Runtime** — not a chatbot, not a RAG demo, not a LangGraph wrapper.

Every AI request inside a company flows through EDITH-X before reaching any LLM. The runtime optimizes cost, latency, accuracy, governance, security, compliance, memory, observability, and reliability — correctness always beats cost.

Target: Fortune 500 companies deploy EDITH-X as their centralized AI orchestration platform.

---

## 2. Infrastructure Dependencies (Local Repos → pip packages)

| Repo | Role |
|---|---|
| `langgraph` | Agent planner — execution graphs, state machines |
| `litellm` | Model abstraction — unified API to 100+ providers |
| `llama_index` | Document ingestion + retrieval |
| `haystack` | NLP pipeline components (extractors, rankers) |
| `qdrant` | Vector DB — semantic cache + memory store |
| `mem0` | Persistent memory (per-user, per-team, per-org) |
| `dspy` | Prompt optimization + compression |
| `fastmcp` | MCP server interface |
| `adk-python` | Google-native agent tooling |
| `ollama` | Local model serving |
| `vllm` | High-throughput local inference |

---

## 3. Implementation Phases

### Phase 0 — Demoable Prototype ⭐ PRIORITY
Thin but complete vertical slice. All 14 module stubs exist with correct interfaces. Full pipeline runs end-to-end. Live demo UI shows real-time cost savings, model routing, cache hits.

**Deliverable:** `docker compose up` → working demo at `localhost:8000` + dashboard at `localhost:8501`

### Phase 1 — Core Runtime
Full optimization engine, LangGraph autonomous loop, DSPy compression, full model router.
**Deliverable:** OpenAI-compatible endpoint with 4-layer cost firewall.

### Phase 2 — Knowledge & Memory
LlamaIndex + Haystack retrieval, Qdrant hybrid search, mem0 scoped memory.
**Deliverable:** RAG-enabled agentic runtime with persistent cross-session memory.

### Phase 3 — Governance
JWT auth, RBAC, tenant isolation, intent classifier, policy engine, verification, reflection.
**Deliverable:** Enterprise-ready governance layer.

### Phase 4 — Enterprise Integrations
Plugin system, MCP server, CLI, GitHub/Slack/Notion/Jira connectors.
**Deliverable:** Full tool-calling + enterprise connectors.

### Phase 5 — Production Hardening
Prometheus/Grafana dashboards, K8s manifests, Cloud Run, CI/CD.
**Deliverable:** Fortune 500 deployable.

---

## 4. Full Request Pipeline

```
Request
  → [M1]  Gateway          — auth, rate-limit, streaming
  → [M2]  Identity         — RBAC, tenant isolation
  → [M3]  Intent Engine    — classify: type, complexity, risk, cost estimate
  → [M4]  Policy Engine    — allowed models, PII, compliance, data residency
  → [M5]  Planner          — LangGraph execution graph construction
  → [M6]  Knowledge Layer  — hybrid search: vector + keyword + graph + SQL
  → [M7]  Context Builder  — merge, deduplicate, rank, compress, token budget
  → [M8]  Optimization     — semantic cache, prompt compression, token estimate
  → [M9]  Model Router     — cost/latency/policy/availability routing decision
  → [M10] Execution        — tool calls, code, browser, APIs, plugins
  → [M11] Verification     — fact-check, confidence, retry/escalate logic
  → [M12] Reflection       — post-execution review, iterative improvement
  → [M13] Memory           — persist learnings user/team/org scoped
  → [M14] Observability    — record cost, latency, tokens, cache hits
Response
```

---

## 5. Project Structure

```
edith-x/
├── edith_x/
│   ├── core/
│   │   ├── interfaces.py      # All Protocol/ABC definitions
│   │   ├── container.py       # DI container (dependency-injector)
│   │   ├── config.py          # Pydantic Settings
│   │   └── pipeline.py        # Main orchestrator
│   ├── modules/
│   │   ├── gateway/
│   │   ├── identity/
│   │   ├── intent/
│   │   ├── policy/
│   │   ├── planner/
│   │   ├── knowledge/
│   │   ├── context/
│   │   ├── optimization/
│   │   ├── router/
│   │   ├── execution/
│   │   ├── verification/
│   │   ├── reflection/
│   │   ├── memory/
│   │   └── observability/
│   ├── interfaces/
│   │   ├── rest/              # FastAPI routes
│   │   ├── sdk/               # Python SDK
│   │   ├── mcp/               # FastMCP server
│   │   └── cli/               # Typer CLI
│   ├── plugins/
│   │   ├── base.py
│   │   ├── github.py
│   │   ├── slack.py
│   │   ├── notion.py
│   │   └── jira.py
│   └── demo/
│       ├── ui.py              # Streamlit dashboard
│       └── scenarios.py       # Pre-built demo scenarios
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── pyproject.toml
└── .env.example
```

---

## 6. Module Interfaces (Python Protocols)

```python
# core/interfaces.py — excerpt

class IntentResult(BaseModel):
    type: Literal["question","task","coding","retrieval","analysis",
                  "summarization","automation","planning","security"]
    complexity: float       # 0.0-1.0
    risk: float             # 0.0-1.0
    estimated_cost_usd: float
    confidence: float
    latency_requirement_ms: int

class PolicyDecision(BaseModel):
    allowed_models: list[str]
    requires_local: bool
    requires_human_approval: bool
    pii_detected: bool
    data_residency: Literal["local","eu","us","any"]
    blocked: bool
    block_reason: str | None

class ModelSelection(BaseModel):
    provider: str           # "ollama"|"vllm"|"openai"|"anthropic"|...
    model: str
    reasoning: str
    estimated_cost_usd: float
    estimated_latency_ms: int

class VerificationResult(BaseModel):
    confidence: float
    grounded: bool
    sources_verified: bool
    should_retry: bool
    escalate_to: str | None

class AgentState(TypedDict):
    goal: str
    run_id: str
    user_id: str
    org_id: str
    intent: IntentResult
    policy: PolicyDecision
    knowledge_chunks: list[KnowledgeChunk]
    context: Context
    model_selection: ModelSelection
    tool_calls: list[ToolCall]
    tool_results: list[ToolResult]
    verification: VerificationResult
    reflection_notes: list[ReflectionNote]
    final_response: str
    iteration_count: int    # max 5 — prevents infinite loops
    messages: Annotated[list, add_messages]
```

---

## 7. 4-Layer Cost Firewall (M8 + M9)

```
L0: Semantic Cache   → Qdrant similarity >= 0.92 → return cached, $0 cost
L1: Local Model      → Ollama/vLLM for simple/medium queries, ~$0 cost
L2: Compressed Cloud → DSPy-compressed prompt to cloud, 40-60% fewer tokens
L3: Full Cloud       → GPT-4o / Claude / Gemini, last resort only
```

Routing decision factors: intent complexity, policy constraints, confidence threshold, model availability, GPU status, estimated cost vs quality tradeoff.

---

## 8. LangGraph Autonomous Agent Graph

```python
# Conditional routing after verification
graph.add_conditional_edges("verify_output", route_after_verify, {
    "retry":    "execute_tools",      # low confidence, retry same model
    "escalate": "escalate_model",     # too complex, upgrade model
    "reflect":  "reflect",            # needs review
    "done":     "generate_response"   # confident result
})

graph.add_conditional_edges("reflect", route_after_reflect, {
    "replan":   "retrieve_knowledge", # missing info
    "done":     "generate_response"
})
```

Each graph node is independently replaceable. Max iterations: 5.

---

## 9. API Specification

### OpenAI-Compatible (Drop-in)
```
POST /v1/chat/completions
Authorization: Bearer <api_key>
{
  "model": "edith-x-auto",
  "messages": [...],
  "stream": true,
  "edith_options": {
    "autonomy": "autonomous",   // "chat"|"tool_use"|"autonomous"
    "memory": true,
    "policy_context": "legal"
  }
}
```

### EDITH-X Native
```
POST   /edith/v1/run              Submit autonomous goal
GET    /edith/v1/run/{id}         Poll run status
DELETE /edith/v1/run/{id}         Cancel run
GET    /edith/v1/metrics          Cost/token/cache metrics
GET    /edith/v1/memory           User memory
DELETE /edith/v1/memory/{id}      Forget memory item
POST   /edith/v1/documents        Index document
GET    /edith/v1/health           Health check
```

---

## 10. Database Schema (Key Tables)

**PostgreSQL:** organizations, users, api_keys, policies, audit_log, pipeline_events

**Qdrant Collections:**
- `edith_semantic_cache` — query embeddings + cached responses
- `edith_knowledge_{org_id}` — org-scoped document embeddings
- `edith_memory_{user_id}` — per-user memory
- `edith_memory_team_{id}` — per-team memory

**Redis:** rate limits, response cache (TTL 1h), session state, model availability

---

## 11. Plugin System

```python
class PluginBase(ABC):
    name: str
    description: str
    version: str

    async def initialize(self, config: dict) -> None: ...
    def get_tools(self) -> list[StructuredTool]: ...
    def get_knowledge_sources(self) -> list[KnowledgeSource]: ...
    async def health_check(self) -> bool: ...
```

Hot-loadable via `registry.load_from_config("plugins.yaml")`.

Built-in Phase 4 plugins: GitHub, Slack, Notion, Jira, Confluence, Google Workspace, Microsoft 365.

---

## 12. Python SDK

```python
from edith_x import Agent

agent = Agent(api_key="ex-...")
result = await agent.run("Summarize all open Jira tickets for sprint 42")
print(result.response)
print(f"Cost: ${result.cost_usd:.4f} (saved ${result.cost_saved_usd:.4f})")

# Streaming
async for chunk in agent.stream("Analyze Q3 sales data"):
    print(chunk, end="", flush=True)

# OpenAI drop-in
from edith_x.compat import openai_client
client = openai_client(base_url="http://localhost:8000")
```

---

## 13. Demo Dashboard (Phase 0 Priority)

Streamlit at `localhost:8501`:
- **Pipeline Visualizer** — animated real-time flow through 14 stages
- **Cost Savings Counter** — $ saved vs direct cloud calls
- **Cache Hit Rate** — semantic cache hit % over time  
- **Model Routing Map** — which queries went local vs cloud + reasoning
- **Live Chat** — full pipeline transparency panel
- **Token Compression** — before/after token counts

---

## 14. Docker Compose

```yaml
services:
  edith-x:    ports: [8000, 8501]
  qdrant:     image: qdrant/qdrant:latest
  postgres:   image: postgres:16
  redis:      image: redis:7-alpine
  ollama:     image: ollama/ollama:latest  # GPU-accelerated
```

---

## 15. Non-Functional Targets

| Metric | Target |
|---|---|
| Cost reduction vs raw cloud | > 60% |
| Cache hit latency | < 50ms |
| Local model latency | < 2s |
| Cloud latency | < 10s |
| Throughput | 1000 req/s (horizontal) |
| Python version | 3.12+ |
| Type safety | Strict mypy + Pydantic v2 |

---

## 16. Coding Principles

- No God classes. No circular imports. No duplicated logic.
- Every module exposes a Protocol interface.
- All dependencies wired through DI container (never imported directly).
- Clean architecture: core domain never imports framework code.
- Composition over inheritance.
- Every component independently testable.

---

## 17. Phase 0 Implementation Checklist

- [ ] `pyproject.toml` with all 11 repo deps + FastAPI, Streamlit, dependency-injector
- [ ] All 14 module stubs implementing correct Protocol interfaces
- [ ] DI container wiring all modules
- [ ] LiteLLM router (OpenAI + Ollama providers)
- [ ] Qdrant semantic cache (basic cosine similarity)
- [ ] FastAPI server: `/v1/chat/completions` + `/edith/v1/run`
- [ ] Streamlit demo dashboard with 5 panels
- [ ] docker-compose with qdrant, postgres, redis, ollama
- [ ] `.env.example` with all required keys
- [ ] 3 pre-built demo scenarios (Q&A, autonomous task, knowledge retrieval)
- [ ] README with `docker compose up` quickstart
