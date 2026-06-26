"""M5 — Planner: LangGraph-based autonomous agent execution graph."""
from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from edith_x.core.config import Settings
from edith_x.core.interfaces import (
    AgentState, AuthContext, Context, PipelineEvent,
    ContextInterface, ExecutionInterface, KnowledgeInterface,
    MemoryInterface, ObservabilityInterface, OptimizationInterface,
    ReflectionInterface, RouterInterface, VerificationInterface,
    IntentResult, PolicyDecision, ModelSelection, ExecutionResult,
    VerificationResult, ReflectionNote, CacheResult,
)

log = structlog.get_logger(__name__)

MAX_ITERATIONS = 5


class PlannerService:
    def __init__(
        self,
        settings: Settings,
        knowledge: KnowledgeInterface,
        context: ContextInterface,
        optimization: OptimizationInterface,
        router: RouterInterface,
        execution: ExecutionInterface,
        verification: VerificationInterface,
        reflection: ReflectionInterface,
        memory: MemoryInterface,
        observability: ObservabilityInterface,
    ) -> None:
        self._settings = settings
        self._knowledge = knowledge
        self._context = context
        self._optimization = optimization
        self._router = router
        self._execution = execution
        self._verification = verification
        self._reflection = reflection
        self._memory = memory
        self._obs = observability
        self._graph = self._build_graph()

    # ── Graph Node Functions ─────────────────────────────────────────────

    async def _node_retrieve(self, state: AgentState) -> AgentState:
        """Retrieve knowledge + memory relevant to the goal."""
        goal = state["goal"]
        user_id = state["user_id"]

        # Parallel: knowledge + memory (both non-blocking)
        chunks = await self._knowledge.retrieve(goal, sources=[], top_k=5)
        memories = await self._memory.get(user_id, goal, top_k=3)

        # Convert memories to chunks
        memory_chunks = [
            {"content": m.content, "source": "user_memory", "score": m.relevance, "id": m.id, "metadata": {}}
            for m in memories
        ]

        state["knowledge_chunks"] = [c.model_dump() for c in chunks] + memory_chunks
        return state

    async def _node_build_context(self, state: AgentState) -> AgentState:
        """Build optimized context within token budget."""
        from edith_x.core.interfaces import KnowledgeChunk
        goal = state["goal"]
        raw_chunks = state.get("knowledge_chunks", [])
        chunks = [KnowledgeChunk(**c) for c in raw_chunks]
        history = []
        for m in state.get("messages", [])[-10:]:
            role = m.type
            if role == "human": role = "user"
            elif role == "ai": role = "assistant"
            history.append({"role": role, "content": m.content})

        ctx = await self._context.build(goal, chunks, history, token_budget=6000)
        state["context"] = ctx.model_dump()
        return state

    async def _node_optimize(self, state: AgentState) -> AgentState:
        """Check semantic cache first — zero cost path."""
        goal = state["goal"]
        cache = await self._optimization.check_cache(goal)
        if cache and cache.hit:
            state["final_response"] = cache.response
            state["cache_hit"] = True
            state["cost_saved_usd"] = cache.saved_cost_usd
            log.info("cache_hit_in_planner", goal=goal[:50])
        else:
            state["cache_hit"] = False
        return state

    async def _node_route(self, state: AgentState) -> AgentState:
        """Select best model for this request."""
        from edith_x.core.interfaces import Context, IntentResult, PolicyDecision
        ctx = Context(**state["context"])
        intent = IntentResult(**state["intent"])
        policy = PolicyDecision(**state["policy"])
        selection = await self._router.route(ctx, policy, intent)
        state["model_selection"] = selection.model_dump()
        return state

    async def _node_execute(self, state: AgentState) -> AgentState:
        """Execute against selected model via LiteLLM."""
        from edith_x.core.interfaces import Context, ModelSelection
        ctx = Context(**state["context"])
        selection = ModelSelection(**state["model_selection"])
        result = await self._execution.execute(ctx, selection)
        state["final_response"] = result.response
        state["tokens_input"] = result.tokens_input
        state["tokens_output"] = result.tokens_output
        state["cost_usd"] = result.cost_usd
        state["latency_ms"] = result.latency_ms
        return state

    async def _node_verify(self, state: AgentState) -> AgentState:
        """Verify the response confidence and grounding."""
        from edith_x.core.interfaces import Context, ExecutionResult, ModelSelection
        ctx = Context(**state["context"])
        sel = ModelSelection(**state["model_selection"])
        result = ExecutionResult(
            run_id=state["run_id"],
            response=state["final_response"],
            model_used=sel.model,
            tokens_input=state.get("tokens_input", 0),
            tokens_output=state.get("tokens_output", 0),
        )
        verification = await self._verification.verify(result, ctx)
        state["verification"] = verification.model_dump()
        return state

    async def _node_reflect(self, state: AgentState) -> AgentState:
        """Reflect on quality and decide next action."""
        from edith_x.core.interfaces import ExecutionResult, ModelSelection, VerificationResult
        sel = ModelSelection(**state["model_selection"])
        result = ExecutionResult(
            run_id=state["run_id"],
            response=state["final_response"],
            model_used=sel.model,
        )
        verification = VerificationResult(**state["verification"])
        note = await self._reflection.reflect(state["goal"], result, verification)
        notes = state.get("reflection_notes", [])
        notes.append(note.model_dump())
        state["reflection_notes"] = notes
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        return state

    async def _node_finalize(self, state: AgentState) -> AgentState:
        """Store cache and memory, record observability."""
        # Store in cache
        if not state.get("cache_hit") and state.get("final_response"):
            await self._optimization.store_cache(state["goal"], state["final_response"])

        # Store in memory
        if state.get("final_response"):
            await self._memory.store(
                state["user_id"],
                f"Q: {state['goal']}\nA: {state['final_response'][:200]}",
                scope="user",
            )

        # Record observability
        sel = state.get("model_selection", {})
        event = PipelineEvent(
            run_id=state["run_id"],
            org_id=state["org_id"],
            user_id=state["user_id"],
            intent_type=state.get("intent", {}).get("type", ""),
            model_selected=sel.get("model", ""),
            provider=sel.get("provider", ""),
            cache_hit=state.get("cache_hit", False),
            tokens_input=state.get("tokens_input", 0),
            tokens_output=state.get("tokens_output", 0),
            cost_usd=state.get("cost_usd", 0.0),
            cost_saved_usd=state.get("cost_saved_usd", 0.0),
            latency_ms=state.get("latency_ms", 0),
            layer=sel.get("layer", "L3_cloud"),
        )
        await self._obs.record(event)
        return state

    # ── Routing Logic ────────────────────────────────────────────────────

    def _route_after_optimize(self, state: AgentState) -> str:
        """If cache hit, skip to finalize. Otherwise route."""
        if state.get("cache_hit"):
            return "finalize"
        return "route"

    def _route_after_reflect(self, state: AgentState) -> str:
        """Decide: retry execution, replan, or finalize."""
        notes = state.get("reflection_notes", [])
        if not notes:
            return "finalize"
        last_note = notes[-1]
        iteration = state.get("iteration_count", 0)

        if iteration >= MAX_ITERATIONS:
            log.warning("max_iterations_reached", run_id=state["run_id"])
            return "finalize"

        action = last_note.get("action", "accept")
        if action == "retry":
            return "execute"
        if action == "replan":
            return "retrieve"
        return "finalize"

    # ── Graph Construction ────────────────────────────────────────────────

    def _build_graph(self) -> Any:
        graph = StateGraph(AgentState)

        graph.add_node("retrieve", self._node_retrieve)
        graph.add_node("build_context", self._node_build_context)
        graph.add_node("optimize", self._node_optimize)
        graph.add_node("route", self._node_route)
        graph.add_node("execute", self._node_execute)
        graph.add_node("verify", self._node_verify)
        graph.add_node("reflect", self._node_reflect)
        graph.add_node("finalize", self._node_finalize)

        graph.add_edge(START, "retrieve")
        graph.add_edge("retrieve", "build_context")
        graph.add_edge("build_context", "optimize")
        graph.add_conditional_edges("optimize", self._route_after_optimize, {
            "finalize": "finalize",
            "route": "route",
        })
        graph.add_edge("route", "execute")
        graph.add_edge("execute", "verify")
        graph.add_edge("verify", "reflect")
        graph.add_conditional_edges("reflect", self._route_after_reflect, {
            "retrieve": "retrieve",
            "execute": "execute",
            "finalize": "finalize",
        })
        graph.add_edge("finalize", END)

        return graph.compile()

    # ── Public API ───────────────────────────────────────────────────────

    async def run(
        self,
        goal: str,
        auth: AuthContext,
        intent: IntentResult,
        policy: PolicyDecision,
        history: list[dict] | None = None,
    ) -> AgentState:
        run_id = str(uuid.uuid4())
        initial_state: AgentState = {
            "goal": goal,
            "run_id": run_id,
            "user_id": auth.user_id,
            "org_id": auth.org_id,
            "intent": intent.model_dump(),
            "policy": policy.model_dump(),
            "knowledge_chunks": [],
            "context": {},
            "model_selection": {},
            "tool_calls": [],
            "tool_results": [],
            "verification": {},
            "reflection_notes": [],
            "final_response": "",
            "iteration_count": 0,
            "cache_hit": False,
            "cost_usd": 0.0,
            "cost_saved_usd": 0.0,
            "tokens_input": 0,
            "tokens_output": 0,
            "latency_ms": 0,
            "messages": [HumanMessage(content=goal)],
        }

        start = time.monotonic()
        final_state = await self._graph.ainvoke(initial_state)
        final_state["latency_ms"] = int((time.monotonic() - start) * 1000)
        return final_state
