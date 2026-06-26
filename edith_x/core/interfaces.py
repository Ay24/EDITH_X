"""
EDITH-X Core Interfaces
All module contracts defined as Python Protocols.
No module imports another directly — all wired through the DI container.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Literal, Protocol, TypedDict, runtime_checkable

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import Annotated


# ─── Shared Data Models ─────────────────────────────────────────────────────

class AuthContext(BaseModel):
    user_id: str
    org_id: str
    email: str
    role: Literal["admin", "member", "viewer"]
    api_key_id: str
    tenant_plan: str = "starter"


class User(BaseModel):
    id: str
    org_id: str
    email: str
    role: str


class Tenant(BaseModel):
    id: str
    name: str
    plan: str
    data_residency: Literal["local", "eu", "us", "any"] = "any"


class AuditEvent(BaseModel):
    org_id: str
    user_id: str
    action: str
    resource: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RateLimitResult(BaseModel):
    allowed: bool
    remaining: int
    reset_at: float


class IntentResult(BaseModel):
    type: Literal[
        "question", "task", "coding", "retrieval", "analysis",
        "summarization", "automation", "planning", "security"
    ]
    complexity: float = Field(ge=0.0, le=1.0)
    risk: float = Field(ge=0.0, le=1.0)
    estimated_cost_usd: float = 0.0
    confidence: float = Field(ge=0.0, le=1.0)
    latency_requirement_ms: int = 5000


class PolicyDecision(BaseModel):
    allowed_models: list[str] = Field(default_factory=list)
    requires_local: bool = False
    requires_human_approval: bool = False
    pii_detected: bool = False
    data_residency: Literal["local", "eu", "us", "any"] = "any"
    blocked: bool = False
    block_reason: str | None = None


class KnowledgeChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    source: str
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Context(BaseModel):
    query: str
    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    history: list[dict[str, str]] = Field(default_factory=list)
    token_count: int = 0
    token_budget: int = 8000
    compressed: bool = False


class ModelSelection(BaseModel):
    provider: Literal["ollama", "vllm", "openai", "anthropic", "google", "groq", "local_llm", "nvidia", "nvidia_nim"]
    model: str
    reasoning: str
    estimated_cost_usd: float = 0.0
    estimated_latency_ms: int = 2000
    layer: Literal["L0_cache", "L1_local", "L2_compressed", "L3_cloud"] = "L3_cloud"


class ToolCall(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool: str
    args: dict[str, Any]


class ToolResult(BaseModel):
    call_id: str
    output: Any
    error: str | None = None
    success: bool = True


class ExecutionResult(BaseModel):
    run_id: str
    response: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    model_used: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


class VerificationResult(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    grounded: bool = True
    sources_verified: bool = True
    should_retry: bool = False
    escalate_to: str | None = None
    issues: list[str] = Field(default_factory=list)


class ReflectionNote(BaseModel):
    observation: str
    suggestion: str
    action: Literal["replan", "retry", "accept"] = "accept"


class CacheResult(BaseModel):
    hit: bool
    response: str = ""
    similarity: float = 0.0
    saved_cost_usd: float = 0.0


class CompressedPrompt(BaseModel):
    original_tokens: int
    compressed_tokens: int
    compressed_text: str
    compression_ratio: float


class MemoryItem(BaseModel):
    id: str
    content: str
    scope: Literal["user", "team", "org"]
    relevance: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineEvent(BaseModel):
    run_id: str
    org_id: str
    user_id: str
    intent_type: str = ""
    model_selected: str = ""
    provider: str = ""
    cache_hit: bool = False
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_saved: int = 0
    cost_usd: float = 0.0
    cost_saved_usd: float = 0.0
    latency_ms: int = 0
    confidence: float = 0.0
    layer: str = "L3_cloud"


class MetricsSummary(BaseModel):
    total_requests: int = 0
    cache_hit_rate: float = 0.0
    avg_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    total_saved_usd: float = 0.0
    avg_latency_ms: float = 0.0
    model_distribution: dict[str, int] = Field(default_factory=dict)
    layer_distribution: dict[str, int] = Field(default_factory=dict)


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSource(BaseModel):
    name: str
    type: Literal["vector", "keyword", "sql", "api", "graph"]
    connection: dict[str, Any] = Field(default_factory=dict)


# ─── LangGraph Agent State ────────────────────────────────────────────────

class AgentState(TypedDict):
    goal: str
    run_id: str
    user_id: str
    org_id: str
    intent: dict[str, Any]
    policy: dict[str, Any]
    knowledge_chunks: list[dict[str, Any]]
    context: dict[str, Any]
    model_selection: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    verification: dict[str, Any]
    reflection_notes: list[dict[str, Any]]
    final_response: str
    iteration_count: int
    cache_hit: bool
    cost_usd: float
    cost_saved_usd: float
    tokens_input: int
    tokens_output: int
    latency_ms: int
    messages: Annotated[list[BaseMessage], add_messages]


# ─── Module Protocol Interfaces ────────────────────────────────────────────

@runtime_checkable
class GatewayInterface(Protocol):
    async def authenticate(self, api_key: str) -> AuthContext: ...
    async def authorize(self, ctx: AuthContext, resource: str) -> bool: ...
    async def rate_limit(self, ctx: AuthContext) -> RateLimitResult: ...


@runtime_checkable
class IdentityInterface(Protocol):
    async def get_user(self, api_key: str) -> User: ...
    async def get_tenant(self, org_id: str) -> Tenant: ...
    async def check_permission(self, user: User, action: str) -> bool: ...
    async def log_audit(self, event: AuditEvent) -> None: ...


@runtime_checkable
class IntentInterface(Protocol):
    async def classify(self, query: str, ctx: AuthContext) -> IntentResult: ...


@runtime_checkable
class PolicyInterface(Protocol):
    async def evaluate(self, intent: IntentResult, ctx: AuthContext) -> PolicyDecision: ...


@runtime_checkable
class PlannerInterface(Protocol):
    async def plan(self, state: AgentState) -> AgentState: ...


@runtime_checkable
class KnowledgeInterface(Protocol):
    async def retrieve(self, query: str, sources: list[str], top_k: int = 10) -> list[KnowledgeChunk]: ...
    async def index(self, document: Document, source: str) -> str: ...


@runtime_checkable
class ContextInterface(Protocol):
    async def build(self, query: str, chunks: list[KnowledgeChunk],
                    history: list[dict[str, str]], token_budget: int) -> Context: ...


@runtime_checkable
class OptimizationInterface(Protocol):
    async def check_cache(self, query: str) -> CacheResult | None: ...
    async def compress_prompt(self, prompt: str, budget: int) -> CompressedPrompt: ...
    async def estimate_tokens(self, text: str) -> int: ...
    async def store_cache(self, query: str, response: str) -> None: ...


@runtime_checkable
class RouterInterface(Protocol):
    async def route(self, context: Context, policy: PolicyDecision,
                    intent: IntentResult) -> ModelSelection: ...


@runtime_checkable
class ExecutionInterface(Protocol):
    async def execute(self, context: Context, selection: ModelSelection) -> ExecutionResult: ...
    async def call_tool(self, tool: str, args: dict[str, Any]) -> ToolResult: ...
    async def stream(self, context: Context, selection: ModelSelection) -> AsyncGenerator[str, None]: ...


@runtime_checkable
class VerificationInterface(Protocol):
    async def verify(self, result: ExecutionResult, context: Context) -> VerificationResult: ...


@runtime_checkable
class ReflectionInterface(Protocol):
    async def reflect(self, goal: str, result: ExecutionResult,
                      verification: VerificationResult) -> ReflectionNote: ...


@runtime_checkable
class MemoryInterface(Protocol):
    async def get(self, user_id: str, query: str, top_k: int = 5) -> list[MemoryItem]: ...
    async def store(self, user_id: str, content: str,
                    scope: Literal["user", "team", "org"] = "user") -> None: ...
    async def forget(self, user_id: str, memory_id: str) -> None: ...


@runtime_checkable
class ObservabilityInterface(Protocol):
    async def record(self, event: PipelineEvent) -> None: ...
    async def get_metrics(self, org_id: str, window: str = "24h") -> MetricsSummary: ...
