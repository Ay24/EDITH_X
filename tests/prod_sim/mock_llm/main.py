"""High-Fidelity Mock LLM Service for Production Simulation & Scale Testing.

Simulates OpenAI-compatible chat completions with:
- Lognormal latency distributions for Local Tier (median 400ms, P99 3s)
  and Cloud Tier (median 1.2s, P99 8s).
- Token-based streaming responses.
- Configurable fault injection (429 RateLimit, 500 InternalError, timeouts).
- Token usage ledger for cost reconciliation audit (T8).
"""
from __future__ import annotations

import asyncio
import random
import time
import uuid
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

app = FastAPI(title="EDITH-X Mock LLM Production Simulator", version="1.0.0")

# Calibration parameters for LogNormal distributions: ln(X) ~ N(mu, sigma)
# For median M and P99 P:
# mu = ln(M), sigma = (ln(P) - ln(M)) / 2.32635
LOCAL_MEDIAN = 0.400  # 400ms
LOCAL_P99 = 3.000     # 3s
LOCAL_MU = np.log(LOCAL_MEDIAN)
LOCAL_SIGMA = (np.log(LOCAL_P99) - np.log(LOCAL_MEDIAN)) / 2.32635

CLOUD_MEDIAN = 1.200  # 1.2s
CLOUD_P99 = 8.000     # 8s
CLOUD_MU = np.log(CLOUD_MEDIAN)
CLOUD_SIGMA = (np.log(CLOUD_P99) - np.log(CLOUD_MEDIAN)) / 2.32635

# In-memory execution ledger for reconciliation
EXECUTION_LOGS: list[dict[str, Any]] = []

# Fault injection state
FAULT_CONFIG = {
    "enabled": True,
    "rate_limit_prob": 0.01,  # 1% HTTP 429
    "server_error_prob": 0.005,  # 0.5% HTTP 500
    "timeout_prob": 0.01,  # 1% timeout (> 30s)
    "forced_failure_mode": None,  # None, "500", "429", "timeout"
}


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "llama-3.2-3b-instruct"
    messages: list[Message]
    stream: bool = False
    temperature: float | None = 0.7
    max_tokens: int | None = 512


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "llama-3.2-3b-instruct", "object": "model", "owned_by": "mock-local"},
            {"id": "meta/llama-3.1-8b-instruct", "object": "model", "owned_by": "mock-local"},
            {"id": "gpt-4o", "object": "model", "owned_by": "mock-cloud"},
            {"id": "gpt-4o-mini", "object": "model", "owned_by": "mock-cloud"},
            {"id": "claude-3-5-sonnet", "object": "model", "owned_by": "mock-cloud"},
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, raw_req: Request):
    t_start = time.perf_counter()
    req_id = f"chatcmpl-mock-{uuid.uuid4().hex[:12]}"

    # Extract query text and compute token estimates
    full_prompt = " ".join(m.content for m in req.messages)
    prompt_tokens = max(1, len(full_prompt) // 4)
    completion_tokens = random.randint(20, 120)

    # 1. Fault Injection Check
    if FAULT_CONFIG["enabled"]:
        forced = FAULT_CONFIG["forced_failure_mode"]
        if forced == "500" or random.random() < FAULT_CONFIG["server_error_prob"]:
            raise HTTPException(status_code=500, detail="Mock LLM Internal Cluster Overload (Fault Injected)")
        if forced == "429" or random.random() < FAULT_CONFIG["rate_limit_prob"]:
            return Response(
                content='{"error": {"message": "Rate limit exceeded. Tier quota exhausted.", "type": "requests", "code": 429}}',
                status_code=429,
                headers={"Retry-After": "2", "Content-Type": "application/json"},
            )
        if forced == "timeout" or random.random() < FAULT_CONFIG["timeout_prob"]:
            await asyncio.sleep(35.0)  # Exceed standard client timeout
            raise HTTPException(status_code=504, detail="Mock LLM Upstream Gateway Timeout")

    # 2. Simulate Latency Distribution based on Model Tier
    is_local = "llama" in req.model.lower() or "local" in req.model.lower()
    if is_local:
        delay = float(np.random.lognormal(LOCAL_MU, LOCAL_SIGMA))
        delay = min(delay, 5.0)  # Bound extreme tail at 5s
    else:
        delay = float(np.random.lognormal(CLOUD_MU, CLOUD_SIGMA))
        delay = min(delay, 12.0)

    # Wait simulated inference latency
    await asyncio.sleep(delay)
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    # Build response text
    response_text = (
        f"[MOCK-VERIFIED RESPONSE: {req.model}]\n"
        f"Processed query with {prompt_tokens} input tokens. "
        f"Operational telemetry: latency={elapsed_ms:.1f}ms, tier={'local' if is_local else 'cloud'}."
    )

    # Record in audit ledger
    log_entry = {
        "req_id": req_id,
        "model": req.model,
        "is_local": is_local,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "latency_ms": elapsed_ms,
        "timestamp": time.time(),
        "has_canary": "CANARY-" in full_prompt,
    }
    EXECUTION_LOGS.append(log_entry)

    # Streaming mode
    if req.stream:
        async def stream_generator():
            words = response_text.split(" ")
            for idx, word in enumerate(words):
                chunk = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": req.model,
                    "choices": [{"index": 0, "delta": {"content": word + " "}, "finish_reason": None}],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.015)  # 15ms per token stream pacing
            yield "data: [DONE]\n\n"

        from fastapi.responses import StreamingResponse
        import json
        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    return {
        "id": req_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


@app.post("/v1/faults")
async def configure_faults(cfg: dict[str, Any]):
    FAULT_CONFIG.update(cfg)
    return {"status": "updated", "current_config": FAULT_CONFIG}


@app.get("/v1/audit/summary")
async def get_audit_summary():
    total_calls = len(EXECUTION_LOGS)
    if total_calls == 0:
        return {"total_calls": 0, "total_prompt_tokens": 0, "total_completion_tokens": 0}
    return {
        "total_calls": total_calls,
        "total_prompt_tokens": sum(e["prompt_tokens"] for e in EXECUTION_LOGS),
        "total_completion_tokens": sum(e["completion_tokens"] for e in EXECUTION_LOGS),
        "total_tokens": sum(e["total_tokens"] for e in EXECUTION_LOGS),
        "canary_calls_received": sum(1 for e in EXECUTION_LOGS if e["has_canary"]),
        "avg_latency_ms": sum(e["latency_ms"] for e in EXECUTION_LOGS) / total_calls,
    }


@app.get("/v1/audit/logs")
async def get_audit_logs(limit: int = 100):
    return EXECUTION_LOGS[-limit:]
