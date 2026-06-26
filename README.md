# ⚡ EDITH-X — Enterprise AI Runtime

> **Enterprise Distributed Intelligence Token Handler — eXtended**
> 
> The AI operating layer between enterprise applications and AI models.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is EDITH-X?

EDITH-X is **not a chatbot**. It is **not another LangChain wrapper**.

EDITH-X is an **Enterprise AI Runtime** — every AI request inside your organization passes through EDITH-X before reaching any LLM. It optimizes for cost, latency, governance, security, and accuracy simultaneously.

```
Your App → EDITH-X → [L0 Cache | L1 Local | L2 Compressed | L3 Cloud] → Response
```

**Typical cost reduction: 60-80%** vs direct cloud API calls.

---

## Architecture

```
Request → Gateway → Identity → Intent → Policy → Planner
                                                    ↓
                              Knowledge ← Context ← ─┤
                                                    ↓
                              Optimization (Cache Check)
                                                    ↓
                              Model Router (4-Layer Cost Firewall)
                                                    ↓
                              Execution (LiteLLM → Any Provider)
                                                    ↓
                              Verification → Reflection → Memory
                                                    ↓
                              Observability → Response
```

### 4-Layer Cost Firewall

| Layer | Provider | Cost | When |
|---|---|---|---|
| 🟢 L0 | Semantic Cache (Qdrant) | $0.00 | Query similarity ≥ 92% |
| 🔵 L1 | Local Model (Ollama/vLLM) | ~$0.00 | Simple/medium queries |
| 🟡 L2 | Compressed Cloud (DSPy) | -40-60% tokens | Complex + policy allows |
| 🔴 L3 | Full Cloud (GPT-4o/Claude) | Full price | Last resort |

### Technology Stack

| Component | Technology |
|---|---|
| Agent Orchestration | LangGraph |
| Model Abstraction | LiteLLM |
| Vector DB | Qdrant |
| Memory | Mem0 |
| Retrieval | LlamaIndex + Haystack |
| Prompt Optimization | DSPy |
| Local Inference | Ollama + vLLM |
| MCP Interface | FastMCP |
| REST API | FastAPI |
| CLI | Typer |

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repo
git clone <your-repo>
cd edith-x

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys (OpenAI, Anthropic, etc.)
# Works without API keys using local Ollama models only

# Start everything
docker compose up -d

# API: http://localhost:8000
# Dashboard: http://localhost:8501
# Docs: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
pip install uv
uv pip install -e ".[dev]"

# Copy env
cp .env.example .env

# Start services (Qdrant, Redis)
docker compose up qdrant redis -d

# Start API server
edith serve

# Start demo dashboard (new terminal)
edith demo
```

---

## Usage

### Python SDK

```python
import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8000/edith/v1/run",
            json={"goal": "Analyze the top 3 risks in enterprise AI deployment"},
            headers={"Authorization": "Bearer demo-key"},
        )
        result = resp.json()
        print(result["response"])
        print(f"Cost: ${result['cost_usd']:.5f} | Saved: ${result['cost_saved_usd']:.5f}")
        print(f"Layer: {result['layer']} | Model: {result['model']}")

asyncio.run(main())
```

### OpenAI Drop-in Replacement

```python
from openai import OpenAI

client = OpenAI(
    api_key="demo-key",
    base_url="http://localhost:8000/v1",
)

response = client.chat.completions.create(
    model="edith-x-auto",
    messages=[{"role": "user", "content": "What is quantum computing?"}],
)
print(response.choices[0].message.content)
```

### CLI

```bash
# Run a goal
edith run "Summarize key risks in deploying AI in healthcare"

# View metrics
edith metrics --window 24h

# Health check
edith health

# Start demo dashboard
edith demo
```

---

## API Reference

### POST `/edith/v1/run`
Run a goal through the autonomous agent.

```json
{
  "goal": "Your goal or question",
  "autonomy": "autonomous",
  "memory": true
}
```

Response includes `cost_usd`, `cost_saved_usd`, `layer`, `model`, `cache_hit`, `tokens_input/output`.

### POST `/v1/chat/completions`
OpenAI-compatible endpoint. Drop-in replacement.

### GET `/edith/v1/metrics`
Cost, cache hit rate, latency, and model distribution metrics.

### POST `/edith/v1/documents`
Index enterprise documents for knowledge retrieval.

### GET `/edith/v1/health`
Runtime health and provider status.

---

## Module Architecture (14 Modules)

| # | Module | Responsibility |
|---|---|---|
| M1 | Gateway | Auth, rate limiting, streaming |
| M2 | Identity | RBAC, tenant isolation |
| M3 | Intent Engine | Query classification, cost estimation |
| M4 | Policy Engine | Compliance, PII, allowed models |
| M5 | Planner | LangGraph autonomous execution graph |
| M6 | Knowledge | Hybrid retrieval (vector + keyword) |
| M7 | Context Builder | Merge, deduplicate, token budget |
| M8 | Optimization | Semantic cache, prompt compression |
| M9 | Model Router | 4-layer cost-aware routing |
| M10 | Execution | LiteLLM + tool calling |
| M11 | Verification | Confidence scoring, grounding |
| M12 | Reflection | Iterative quality improvement |
| M13 | Memory | Per-user/team/org persistent memory |
| M14 | Observability | Cost, latency, cache metrics |

---

## Implementation Roadmap

- ✅ **Phase 0** — Demoable prototype (current)
- 🔲 **Phase 1** — Full optimization engine + DSPy compression
- 🔲 **Phase 2** — LlamaIndex/Haystack retrieval + Qdrant hybrid search
- 🔲 **Phase 3** — JWT auth, RBAC, policy engine, verification loop
- 🔲 **Phase 4** — Plugin system (GitHub, Slack, Notion, Jira) + MCP server
- 🔲 **Phase 5** — Prometheus/Grafana, Kubernetes, Cloud Run, CI/CD

---

## Configuration

See `.env.example` for all configuration options. Key settings:

```env
# Works with zero API keys (local Ollama only)
OLLAMA_DEFAULT_MODEL=llama3.2:3b

# Add cloud keys for cloud routing
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Cost thresholds
MAX_COST_PER_REQUEST_USD=0.10
CACHE_SIMILARITY_THRESHOLD=0.92
```

---

## License

MIT — Built for enterprise, open for all.
