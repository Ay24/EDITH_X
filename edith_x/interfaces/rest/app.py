"""EDITH-X FastAPI REST Interface — OpenAI-compatible + native endpoints."""
from __future__ import annotations

import time
import uuid
from typing import Any, AsyncGenerator

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from edith_x.core.container import container
from edith_x.core.interfaces import AuthContext

log = structlog.get_logger(__name__)

app = FastAPI(
    title="EDITH-X Enterprise AI Runtime",
    description="Enterprise Distributed Intelligence Token Handler — eXtended",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/client", StaticFiles(directory=static_dir, html=True), name="client")


# ── Auth Dependency ──────────────────────────────────────────────────────────

async def get_auth(authorization: str = Header(default="Bearer demo-key")) -> AuthContext:
    api_key = authorization.replace("Bearer ", "").strip()
    gateway = container.gateway()
    return await gateway.authenticate(api_key)


# ── OpenAI-Compatible Models ─────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str


class EdithOptions(BaseModel):
    autonomy: str = "autonomous"
    memory: bool = True
    policy_context: str = ""


class ChatCompletionRequest(BaseModel):
    model: str = "edith-x-auto"
    messages: list[ChatMessage]
    stream: bool = False
    max_tokens: int | None = None
    temperature: float | None = None
    edith_options: EdithOptions | None = None


class GoalRequest(BaseModel):
    goal: str
    autonomy: str = "autonomous"
    memory: bool = True


class DocumentRequest(BaseModel):
    content: str
    source: str
    metadata: dict[str, Any] = {}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/edith/v1/health")
async def health() -> dict:
    settings = container.config()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "demo_mode": settings.demo_mode,
        "providers": {
            "local_llm": settings.local_llm_host,
            "has_openai": bool(settings.openai_api_key),
            "has_anthropic": bool(settings.anthropic_api_key),
        },
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    auth: AuthContext = Depends(get_auth),
):
    """OpenAI-compatible endpoint — drop-in replacement."""
    # Extract the last user message as the goal
    goal = next(
        (m.content for m in reversed(request.messages) if m.role == "user"),
        "Hello"
    )
    history = [{"role": m.role, "content": m.content} for m in request.messages[:-1]]

    intent_svc = container.intent()
    policy_svc = container.policy()
    planner = container.planner()

    intent = await intent_svc.classify(goal, auth)
    policy = await policy_svc.evaluate(intent, auth)

    if policy.blocked:
        raise HTTPException(status_code=403, detail=policy.block_reason)

    if request.stream:
        return StreamingResponse(
            _stream_response(goal, auth, intent, policy, planner),
            media_type="text/event-stream",
        )

    state = await planner.run(goal, auth, intent, policy, history)
    response_text = state.get("final_response", "No response generated")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": state.get("model_selection", {}).get("model", "edith-x-auto"),
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response_text},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": state.get("tokens_input", 0),
            "completion_tokens": state.get("tokens_output", 0),
            "total_tokens": state.get("tokens_input", 0) + state.get("tokens_output", 0),
        },
        "edith_metadata": {
            "cache_hit": state.get("cache_hit", False),
            "cost_usd": state.get("cost_usd", 0.0),
            "cost_saved_usd": state.get("cost_saved_usd", 0.0),
            "layer": state.get("model_selection", {}).get("layer", "L3_cloud"),
            "run_id": state.get("run_id", ""),
        },
    }


async def _stream_response(goal, auth, intent, policy, planner) -> AsyncGenerator[str, None]:
    import json
    state = await planner.run(goal, auth, intent, policy)
    content = state.get("final_response", "")
    # Stream word by word for demo effect
    words = content.split(" ")
    for i, word in enumerate(words):
        chunk = {
            "id": f"chatcmpl-stream-{i}",
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"content": word + " "}, "index": 0}],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        import asyncio
        await asyncio.sleep(0.02)
    yield "data: [DONE]\n\n"


@app.post("/edith/v1/run")
async def run_goal(
    request: GoalRequest,
    auth: AuthContext = Depends(get_auth),
) -> dict:
    """Native EDITH-X endpoint for autonomous goal execution."""
    intent_svc = container.intent()
    policy_svc = container.policy()
    planner = container.planner()

    intent = await intent_svc.classify(request.goal, auth)
    policy = await policy_svc.evaluate(intent, auth)

    if policy.blocked:
        raise HTTPException(status_code=403, detail=policy.block_reason)

    state = await planner.run(request.goal, auth, intent, policy)
    return {
        "run_id": state.get("run_id"),
        "response": state.get("final_response"),
        "cache_hit": state.get("cache_hit", False),
        "cost_usd": state.get("cost_usd", 0.0),
        "cost_saved_usd": state.get("cost_saved_usd", 0.0),
        "tokens_input": state.get("tokens_input", 0),
        "tokens_output": state.get("tokens_output", 0),
        "latency_ms": state.get("latency_ms", 0),
        "model": state.get("model_selection", {}).get("model", ""),
        "layer": state.get("model_selection", {}).get("layer", ""),
        "intent": intent.type,
        "iterations": state.get("iteration_count", 1),
    }


@app.get("/edith/v1/metrics")
async def get_metrics(
    window: str = "24h",
    auth: AuthContext = Depends(get_auth),
) -> dict:
    obs = container.observability()
    metrics = await obs.get_metrics(auth.org_id, window)
    return {
        **metrics.model_dump(),
        "cumulative_savings_usd": obs.get_cumulative_savings(),
        "cumulative_cost_usd": obs.get_cumulative_cost(),
        "recent_events": [e.model_dump() for e in obs.get_recent_events(20)],
    }


@app.post("/edith/v1/documents")
async def index_document(
    request: DocumentRequest,
    auth: AuthContext = Depends(get_auth),
) -> dict:
    from edith_x.core.interfaces import Document
    knowledge = container.knowledge()
    doc = Document(content=request.content, source=request.source, metadata=request.metadata)
    doc_id = await knowledge.index(doc, request.source)
    return {"id": doc_id, "source": request.source, "status": "indexed"}


@app.get("/edith/v1/memory")
async def get_memory(
    query: str = "",
    auth: AuthContext = Depends(get_auth),
) -> dict:
    memory = container.memory()
    items = await memory.get(auth.user_id, query or "recent")
    return {"items": [i.model_dump() for i in items], "user_id": auth.user_id}
