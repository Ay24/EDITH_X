"""M10 — Execution Engine: Calls LLMs via LiteLLM with resilient multi-provider fallback waterfall."""
from __future__ import annotations

import time
import uuid
from typing import AsyncGenerator

import litellm
import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import (
    Context, ExecutionResult, ModelSelection, ToolCall, ToolResult,
)

log = structlog.get_logger(__name__)

litellm.drop_params = True  # Ignore unsupported params per provider
litellm.telemetry = False   # Disable network telemetry in test/enterprise environments


class ExecutionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._configure_litellm()

    def _configure_litellm(self) -> None:
        if self._settings.openai_api_key:
            litellm.openai_key = self._settings.openai_api_key
        if self._settings.anthropic_api_key:
            litellm.anthropic_key = self._settings.anthropic_api_key
        if self._settings.nvidia_api_key:
            import os
            os.environ["NVIDIA_API_KEY"] = self._settings.nvidia_api_key
            os.environ["NVIDIA_NIM_API_KEY"] = self._settings.nvidia_api_key

    def _build_messages(self, context: Context) -> list[dict]:
        messages = []
        # System prompt
        messages.append({
            "role": "system",
            "content": (
                "You are EDITH-X, an enterprise AI runtime. "
                "Be precise, factual, and cite sources when available. "
                "If knowledge context is provided, use it to ground your response."
            ),
        })
        # Knowledge context
        if context.chunks:
            context_text = "\n\n".join(
                f"[Source: {c.source}]\n{c.content}" for c in context.chunks
            )
            messages.append({
                "role": "user",
                "content": f"<knowledge_context>\n{context_text}\n</knowledge_context>",
            })
        # History
        for msg in context.history[-10:]:  # Last 10 turns
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        # Current query
        messages.append({"role": "user", "content": context.query})
        return messages

    def _resolve_model_kwargs(self, provider: str, model_name: str) -> dict:
        """Map provider and model name to LiteLLM arguments."""
        kwargs: dict = {
            "model": model_name,
            "max_tokens": 2048,
            "temperature": 0.3,
        }

        if provider == "local_llm":
            kwargs["model"] = f"openai/{model_name}"
            kwargs["api_base"] = self._settings.local_llm_host
        elif provider in ("nvidia", "nvidia_nim"):
            actual_model = model_name.replace("nvidia_nim/", "").replace("nvidia/", "")
            kwargs["model"] = f"openai/{actual_model}"
            kwargs["api_base"] = "https://integrate.api.nvidia.com/v1"
            kwargs["api_key"] = self._settings.nvidia_api_key
        elif provider == "google":
            kwargs["model"] = f"gemini/{model_name}"
        elif provider == "openai":
            if self._settings.openai_api_key:
                kwargs["api_key"] = self._settings.openai_api_key
        elif provider == "anthropic":
            if self._settings.anthropic_api_key:
                kwargs["api_key"] = self._settings.anthropic_api_key

        return kwargs

    def _get_fallback_candidates(self, primary_provider: str, primary_model: str) -> list[tuple[str, str]]:
        """Ordered list of fallback (provider, model) candidates."""
        candidates = []

        # 1. Secondary Cloud Fallbacks
        if primary_provider in ("nvidia", "nvidia_nim"):
            if self._settings.openai_api_key:
                candidates.append(("openai", "gpt-4o-mini"))
            if self._settings.anthropic_api_key:
                candidates.append(("anthropic", "claude-3-haiku-20240307"))
        elif primary_provider == "openai":
            if self._settings.nvidia_api_key:
                candidates.append(("nvidia_nim", "meta/llama-3.1-70b-instruct"))
            if self._settings.anthropic_api_key:
                candidates.append(("anthropic", "claude-3-haiku-20240307"))
        elif primary_provider == "anthropic":
            if self._settings.openai_api_key:
                candidates.append(("openai", "gpt-4o-mini"))

        # 2. Local Fallback (Ollama / vLLM / LM Studio)
        if self._settings.local_model_list:
            candidates.append(("local_llm", self._settings.local_model_list[0]))

        return [c for c in candidates if not (c[0] == primary_provider and c[1] == primary_model)]

    async def execute(self, context: Context, selection: ModelSelection) -> ExecutionResult:
        run_id = str(uuid.uuid4())
        messages = self._build_messages(context)
        start = time.monotonic()

        # 1. Primary Attempt
        primary_kwargs = self._resolve_model_kwargs(selection.provider, selection.model)
        primary_kwargs["messages"] = messages

        try:
            response = await litellm.acompletion(**primary_kwargs)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            content = response.choices[0].message.content or ""
            usage = response.usage

            tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
            tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0

            log.info(
                "execution_complete",
                model=selection.model,
                provider=selection.provider,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=elapsed_ms,
            )

            return ExecutionResult(
                run_id=run_id,
                response=content,
                model_used=selection.model,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                cost_usd=selection.estimated_cost_usd,
                latency_ms=elapsed_ms,
                failover_active=False,
            )

        except Exception as primary_err:
            log.warning(
                "primary_execution_failed_initiating_waterfall",
                provider=selection.provider,
                model=selection.model,
                error=str(primary_err),
            )

            # 2. Resilient Fallback Waterfall
            fallbacks = self._get_fallback_candidates(selection.provider, selection.model)
            for fb_provider, fb_model in fallbacks:
                log.info("attempting_fallback_provider", provider=fb_provider, model=fb_model)
                fb_kwargs = self._resolve_model_kwargs(fb_provider, fb_model)
                fb_kwargs["messages"] = messages
                try:
                    fb_response = await litellm.acompletion(**fb_kwargs)
                    elapsed_ms = int((time.monotonic() - start) * 1000)
                    fb_content = fb_response.choices[0].message.content or ""
                    fb_usage = fb_response.usage

                    fb_tokens_in = getattr(fb_usage, "prompt_tokens", 0) if fb_usage else 0
                    fb_tokens_out = getattr(fb_usage, "completion_tokens", 0) if fb_usage else 0

                    log.info(
                        "fallback_execution_succeeded",
                        fallback_provider=fb_provider,
                        fallback_model=fb_model,
                        latency_ms=elapsed_ms,
                    )

                    return ExecutionResult(
                        run_id=run_id,
                        response=fb_content,
                        model_used=fb_model,
                        tokens_input=fb_tokens_in,
                        tokens_output=fb_tokens_out,
                        cost_usd=0.0 if fb_provider == "local_llm" else 0.0005,
                        latency_ms=elapsed_ms,
                        failover_active=True,
                        failover_reason=str(primary_err),
                    )
                except Exception as fb_err:
                    log.warning(
                        "fallback_attempt_failed",
                        fallback_provider=fb_provider,
                        fallback_model=fb_model,
                        error=str(fb_err),
                    )
                    continue

            # 3. Graceful degradation if every provider is unreachable
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return ExecutionResult(
                run_id=run_id,
                response=(
                    f"EDITH-X Resilient Mesh: Upstream models are temporarily unavailable ({primary_err}). "
                    "All fallback candidates exhausted."
                ),
                model_used=selection.model,
                tokens_input=0,
                tokens_output=0,
                cost_usd=0.0,
                latency_ms=elapsed_ms,
                failover_active=True,
                failover_reason=str(primary_err),
            )

    async def stream(
        self, context: Context, selection: ModelSelection
    ) -> AsyncGenerator[str, None]:
        messages = self._build_messages(context)
        kwargs = self._resolve_model_kwargs(selection.provider, selection.model)
        kwargs["messages"] = messages
        kwargs["stream"] = True

        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta

    async def call_tool(self, tool_call: ToolCall) -> ToolResult:
        return ToolResult(call_id=tool_call.id, output=None, success=False, error="Tool not implemented")
