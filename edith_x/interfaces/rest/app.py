"""EDITH-X FastAPI REST Interface — OpenAI-compatible + native endpoints."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from edith_x.core.container import container
from edith_x.core.interfaces import AuthContext
from edith_x.interfaces.rest.multipart import parse_multipart_form

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


@app.get("/")
@app.get("/dashboard")
async def root_dashboard():
    """Serve the Enterprise Multi-Page Control Center UI."""
    return FileResponse(os.path.join(static_dir, "index.html"))


# ── Auth Dependency ──────────────────────────────────────────────────────────

async def get_auth(authorization: str = Header(default="Bearer demo-key")) -> AuthContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header scheme. Bearer required.")
    api_key = authorization.replace("Bearer ", "").strip()
    if not api_key:
        raise HTTPException(status_code=401, detail="API key is required.")
    gateway = container.gateway()
    auth = await gateway.authenticate(api_key)
    if not auth:
        raise HTTPException(status_code=401, detail="Invalid, expired, or forged API credentials.")
    return auth


# ── OpenAI-Compatible Models ─────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None


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
    tools: list[dict] | None = None
    tool_choice: Any | None = "auto"
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
        (m.content for m in reversed(request.messages) if m.role == "user" and m.content),
        "Hello"
    )
    history = [{"role": m.role, "content": m.content} for m in request.messages[:-1]]

    # OpenAI Function Calling dispatch
    target_tool = None
    if request.tools and request.tool_choice != "none":
        has_tool_response = any(m.role == "tool" for m in request.messages)
        if not has_tool_response:
            if isinstance(request.tool_choice, dict) and "function" in request.tool_choice:
                target_tool = request.tool_choice["function"].get("name")
            elif isinstance(request.tool_choice, str) and request.tool_choice not in ("auto", "none", "required"):
                target_tool = request.tool_choice
            elif request.tool_choice == "required" and len(request.tools) > 0:
                target_tool = request.tools[0].get("function", {}).get("name")
            elif request.tool_choice == "auto":
                for t in request.tools:
                    fname = t.get("function", {}).get("name", "")
                    if fname == "generate_document" and any(k in goal.lower() for k in ("pdf", "pptx", "xlsx", "document", "report", "presentation")):
                        target_tool = fname
                        break

    if target_tool:
        doc_type = "pdf"
        if "pptx" in goal.lower():
            doc_type = "pptx"
        elif "xlsx" in goal.lower():
            doc_type = "xlsx"
        args = {
            "document_type": doc_type,
            "title": "Document Report",
            "content": goal,
        }
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model or "edith-x-auto",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": target_tool,
                            "arguments": json.dumps(args),
                        }
                    }]
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {
                "prompt_tokens": len(goal.split()),
                "completion_tokens": 15,
                "total_tokens": len(goal.split()) + 15,
            },
            "edith_metadata": {
                "cache_hit": False,
                "cost_usd": 0.0,
                "cost_saved_usd": 0.0,
                "layer": "L0_tool_dispatch",
                "run_id": f"tool-{uuid.uuid4().hex[:8]}",
            },
        }

    intent_svc = container.intent()
    policy_svc = container.policy()
    planner = container.planner()

    # Pre-execution PII & Secret Redaction (BUG-002)
    sanitized_goal, _, _ = policy_svc.sanitize_payload(goal)

    intent = await intent_svc.classify(sanitized_goal, auth)
    policy = await policy_svc.evaluate(intent, auth, query=sanitized_goal)

    if policy.blocked:
        raise HTTPException(status_code=403, detail=policy.block_reason)

    if request.stream:
        return StreamingResponse(
            _stream_response(sanitized_goal, auth, intent, policy, planner),
            media_type="text/event-stream",
        )

    tool_msgs = [m for m in request.messages if m.role == "tool"]
    if tool_msgs:
        latest_tool = tool_msgs[-1]
        synthesis_goal = f"Tool result for '{goal}': {latest_tool.content}. Please summarize cleanly."
        state = await planner.run(synthesis_goal, auth, intent, policy, history)
        raw_response = state.get("final_response") or f"Operation completed: {latest_tool.content}"
    else:
        state = await planner.run(sanitized_goal, auth, intent, policy, history)
        raw_response = state.get("final_response", "No response generated")
    # Output DLP Sanitization
    response_text, _, _ = policy_svc.sanitize_payload(raw_response)

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
            "layer": "L0_cache" if state.get("cache_hit") else state.get("model_selection", {}).get("layer", "L3_cloud"),
            "run_id": state.get("run_id", ""),
        },
    }


async def _stream_response(goal, auth, intent, policy, planner) -> AsyncGenerator[str, None]:
    import json
    policy_svc = container.policy()
    state = await planner.run(goal, auth, intent, policy)
    raw_content = state.get("final_response", "")
    # Output DLP & Redaction on stream content
    content, _, _ = policy_svc.sanitize_payload(raw_content)
    # Stream word by word for demo effect
    words = content.split(" ")
    for i, word in enumerate(words):
        chunk = {
            "id": f"chatcmpl-stream-{i}",
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"content": word + (" " if i < len(words) - 1 else "")}, "index": 0}],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        import asyncio
        await asyncio.sleep(0.01)
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

    # Pre-execution PII & Secret Redaction (BUG-002)
    sanitized_goal, _, _ = policy_svc.sanitize_payload(request.goal)

    intent = await intent_svc.classify(sanitized_goal, auth)
    policy = await policy_svc.evaluate(intent, auth, query=sanitized_goal)

    if policy.blocked:
        raise HTTPException(status_code=403, detail=policy.block_reason)

    state = await planner.run(sanitized_goal, auth, intent, policy)
    raw_response = state.get("final_response", "")
    # Output DLP Sanitization
    sanitized_response, _, _ = policy_svc.sanitize_payload(raw_response)
    return {
        "run_id": state.get("run_id"),
        "response": sanitized_response,
        "cache_hit": state.get("cache_hit", False),
        "cost_usd": state.get("cost_usd", 0.0),
        "cost_saved_usd": state.get("cost_saved_usd", 0.0),
        "tokens_input": state.get("tokens_input", 0),
        "tokens_output": state.get("tokens_output", 0),
        "latency_ms": state.get("latency_ms", 0),
        "model": state.get("model_selection", {}).get("model", ""),
        "layer": "L0_cache" if state.get("cache_hit") else state.get("model_selection", {}).get("layer", ""),
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


@app.get("/metrics")
async def prometheus_metrics():
    from fastapi.responses import PlainTextResponse
    obs = container.observability()
    return PlainTextResponse(obs.generate_prometheus_metrics(), media_type="text/plain; version=0.0.4")


class ScanRequest(BaseModel):
    text: str


@app.post("/edith/v1/policy/scan")
async def scan_policy(
    request: ScanRequest,
    auth: AuthContext = Depends(get_auth),
) -> dict:
    """Scan and sanitize text against enterprise PII and Shannon entropy firewall."""
    from edith_x.modules.policy.firewall import EnterprisePIIFirewall
    firewall = EnterprisePIIFirewall()
    redacted, matches = firewall.sanitize(request.text)
    return {
        "original": request.text,
        "redacted": redacted,
        "has_pii_or_secrets": len(matches) > 0,
        "match_count": len(matches),
        "matches": [m if isinstance(m, dict) else m.to_dict() for m in matches],
    }


@app.get("/edith/v1/knowledge/query")
async def query_knowledge(
    q: str,
    top_k: int = 5,
    auth: AuthContext = Depends(get_auth),
) -> dict:
    """Direct query against Qdrant hybrid vector & lexical collection."""
    knowledge = container.knowledge()
    chunks = await knowledge.retrieve(q, top_k=top_k)
    return {"query": q, "chunks": [c.model_dump() for c in chunks]}


# ── M15 Document Pipeline & GDPR Endpoints ────────────────────────────────────

@app.post("/v1/files")
async def upload_file(
    request: Request,
    auth: AuthContext = Depends(get_auth),
) -> dict:
    """OpenAI-compatible file upload endpoint with tenant isolation (pure stdlib multipart)."""
    body = await request.body()
    content_type = request.headers.get("content-type", "")
    content, filename, purpose = parse_multipart_form(body, content_type)
    file_hash = hashlib.sha256(content).hexdigest()
    file_id = f"file-{file_hash[:16]}"

    tenant_dir = Path(f"storage/tenants/{auth.org_id}/files")
    tenant_dir.mkdir(parents=True, exist_ok=True)
    file_path = tenant_dir / f"{file_id}_{filename}"
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "id": file_id,
        "object": "file",
        "bytes": len(content),
        "created_at": int(time.time()),
        "filename": filename,
        "purpose": purpose,
        "status": "processed",
        "file_hash": file_hash,
    }


class FileSummarizeRequest(BaseModel):
    file_id: str
    prompt: str = "Summarize key information and actionable points."


@app.post("/edith/v1/files/summarize")
async def summarize_file(
    request: FileSummarizeRequest,
    auth: AuthContext = Depends(get_auth),
) -> dict:
    """Hierarchical map-reduce summarization with per-chunk PII redaction and $0 repeat cache."""
    from edith_x.modules.document.pipeline import DocumentPipeline
    tenant_dir = Path(f"storage/tenants/{auth.org_id}/files")
    matching_files = list(tenant_dir.glob(f"{request.file_id}_*"))
    if not matching_files:
        raise HTTPException(status_code=404, detail=f"File {request.file_id} not found for tenant {auth.org_id}")

    target_path = matching_files[0]
    filename = target_path.name.split("_", 1)[1] if "_" in target_path.name else target_path.name
    with open(target_path, "rb") as f:
        file_bytes = f.read()

    pipeline = DocumentPipeline(cache=container.optimization().cache)
    parsed = pipeline.parse_document(file_bytes=file_bytes, filename=filename)
    result = await pipeline.summarize_document(
        parsed=parsed,
        org_id=auth.org_id,
        prompt=request.prompt,
    )
    return {
        "file_id": request.file_id,
        "summary": result.summary,
        "file_hash": result.sha256,
        "chunks_processed": result.chunks_processed,
        "cache_hit": result.cache_hit,
        "cost_usd": result.cost_usd,
    }


class PrivacyErasureRequest(BaseModel):
    user_id: str
    reason: str = "GDPR Article 17 Right to Erasure"


@app.post("/edith/v1/privacy/erasure")
async def gdpr_privacy_erasure(
    request: PrivacyErasureRequest,
    auth: AuthContext = Depends(get_auth),
) -> dict:
    """Enforce GDPR Right to Erasure across cache, memory, and record cryptographic tombstone in audit ledger."""
    # 1. Purge cache entries
    opt_svc = container.optimization()
    purged_cache_count = opt_svc.purge_user_data(request.user_id)

    # 2. Purge user memories
    mem_svc = container.memory()
    purged_mem_count = await mem_svc.purge_user_memory(request.user_id)

    # 3. Log cryptographic tombstone in audit ledger
    ledger = container.identity().audit_ledger
    tombstone_event = ledger.record_event(
        action="gdpr_erasure_tombstone",
        user_id=request.user_id,
        org_id=auth.org_id,
        details={
            "reason": request.reason,
            "purged_cache_entries": purged_cache_count,
            "purged_memory_records": purged_mem_count,
            "initiated_by_role": auth.role,
            "legal_basis": "GDPR Art. 17 / India DPDP Act 2023 Sec. 12",
        },
    )

    return {
        "status": "erased",
        "user_id": request.user_id,
        "org_id": auth.org_id,
        "cache_entries_purged": purged_cache_count,
        "memory_records_purged": purged_mem_count,
        "tombstone_hash": tombstone_event["entry_hash"],
        "timestamp": tombstone_event["timestamp"],
    }
