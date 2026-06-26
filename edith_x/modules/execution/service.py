"""M10 — Execution Engine: Calls LLMs via LiteLLM with streaming support."""
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

    def _resolve_model(self, selection: ModelSelection) -> str:
        """Map provider:model to LiteLLM format."""
        if selection.provider == "local_llm":
            return f"openai/{selection.model}"  # LM Studio uses OpenAI format
        if selection.provider == "nvidia":
            return selection.model # litellm supports nvidia/ prefix directly
        if selection.provider == "anthropic":
            return selection.model
        if selection.provider == "google":
            return f"gemini/{selection.model}"
        return selection.model

    async def execute(self, context: Context, selection: ModelSelection) -> ExecutionResult:
        run_id = str(uuid.uuid4())
        messages = self._build_messages(context)
        model = self._resolve_model(selection)

        start = time.monotonic()
        try:
            kwargs: dict = {
                "model": model,
                "messages": messages,
                "max_tokens": 2048,
                "temperature": 0.3,
            }
            if selection.provider == "local_llm":
                kwargs["api_base"] = self._settings.local_llm_host
            elif selection.provider == "nvidia_nim":
                # Bypass litellm's buggy nvidia_nim provider by using generic openai routing
                kwargs["api_base"] = "https://integrate.api.nvidia.com/v1"
                kwargs["api_key"] = self._settings.nvidia_api_key
                # Remove nvidia_nim/ prefix and replace with openai/
                actual_model = model.replace("nvidia_nim/", "")
                kwargs["model"] = f"openai/{actual_model}"

            response = await litellm.acompletion(**kwargs)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            content = response.choices[0].message.content or ""
            usage = response.usage

            log.info(
                "execution_complete",
                model=model,
                tokens_in=usage.prompt_tokens if usage else 0,
                tokens_out=usage.completion_tokens if usage else 0,
                latency_ms=elapsed_ms,
            )

            return ExecutionResult(
                run_id=run_id,
                response=content,
                model_used=model,
                tokens_input=usage.prompt_tokens if usage else 0,
                tokens_output=usage.completion_tokens if usage else 0,
                cost_usd=selection.estimated_cost_usd,
                latency_ms=elapsed_ms,
            )
        except Exception as e:
            log.error("execution_failed", model=model, error=str(e))
            # Try fallback to local
            if selection.provider != "local_llm" and self._settings.has_local_models:
                log.info("trying_local_fallback")
                fallback_model = f"openai/{self._settings.local_model_list[0]}"
                try:
                    response = await litellm.acompletion(
                        model=fallback_model,
                        messages=messages,
                        api_base=self._settings.local_llm_host,
                        max_tokens=1024,
                    )
                    content = response.choices[0].message.content or ""
                    return ExecutionResult(
                        run_id=run_id,
                        response=content,
                        model_used=fallback_model,
                        tokens_input=0,
                        tokens_output=0,
                        cost_usd=0.0,
                        latency_ms=int((time.monotonic() - start) * 1000),
                    )
                except Exception as fe:
                    log.error("fallback_failed", error=str(fe))

            return ExecutionResult(
                run_id=run_id,
                response=f"Execution failed: {e}. Please check your API keys and model availability.",
                model_used=model,
                latency_ms=int((time.monotonic() - start) * 1000),
            )

    async def stream(
        self, context: Context, selection: ModelSelection
    ) -> AsyncGenerator[str, None]:
        messages = self._build_messages(context)
        model = self._resolve_model(selection)
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": 2048,
            "temperature": 0.3,
        }
        if selection.provider == "local_llm":
            kwargs["api_base"] = self._settings.local_llm_host
        try:
            async for chunk in await litellm.acompletion(**kwargs):
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            yield f"[Stream error: {e}]"

    async def call_tool(self, tool: str, args: dict) -> ToolResult:
        """Phase 0 stub. Phase 4: full tool execution."""
        return ToolResult(
            call_id=str(uuid.uuid4()),
            output=f"[Tool '{tool}' called with args {args}] — Phase 4 implementation pending",
            success=True,
        )
