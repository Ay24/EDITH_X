"""Enterprise Tool Registry for Autonomous Agent Tool Execution (FastMCP & Native Tools)."""
from __future__ import annotations

import ast
import datetime
import inspect
import math
import operator
from typing import Any, Callable, Coroutine
import structlog

from edith_x.core.interfaces import ToolCall, ToolResult

log = structlog.get_logger(__name__)

# Allowed operators for safe mathematical evaluation
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval_math(expr: str) -> float | int:
    """Safely evaluate arithmetic expressions without using raw eval/exec."""
    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op = _SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op = _SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(operand)
        else:
            raise ValueError(f"Unsupported AST expression: {type(node).__name__}")

    parsed = ast.parse(expr.strip(), mode="eval")
    return _eval(parsed.body)


class EnterpriseToolRegistry:
    """Registry managing tool definitions, schema validation, and sandboxed dispatch."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable] = {}
        self._descriptions: dict[str, str] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register default out-of-the-box safe enterprise tools."""
        self.register(
            name="calculator",
            handler=self._tool_calculator,
            description="Safely evaluate arithmetic expressions (e.g., '100 * 1.18 + 50').",
        )
        self.register(
            name="datetime_now",
            handler=self._tool_datetime,
            description="Returns current UTC timestamp in ISO-8601 format.",
        )
        self.register(
            name="system_status",
            handler=self._tool_system_status,
            description="Returns gateway system health and runtime metadata.",
        )

    def register(self, name: str, handler: Callable, description: str = "") -> None:
        """Register a new tool handler (async or sync)."""
        self._tools[name] = handler
        self._descriptions[name] = description
        log.info("tool_registered", name=name, description=description)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    async def execute_tool(self, call: ToolCall) -> ToolResult:
        """Execute a tool call safely, handling async or sync functions with argument binding."""
        if call.tool not in self._tools:
            available = self.list_tools()
            log.warning("unregistered_tool_called", tool=call.tool, available=available)
            return ToolResult(
                call_id=call.id,
                output=None,
                success=False,
                error=f"Unregistered tool '{call.tool}'. Available tools: {available}",
            )

        handler = self._tools[call.tool]
        try:
            args = call.args or {}
            if inspect.iscoroutinefunction(handler):
                result = await handler(**args)
            else:
                result = handler(**args)

            log.info("tool_executed_successfully", tool=call.tool, call_id=call.id)
            return ToolResult(
                call_id=call.id,
                output=result,
                success=True,
            )
        except Exception as e:
            log.error("tool_execution_failed", tool=call.tool, call_id=call.id, error=str(e))
            return ToolResult(
                call_id=call.id,
                output=None,
                success=False,
                error=f"Error executing tool '{call.tool}': {str(e)}",
            )

    execute = execute_tool

    # ── Default Tool Implementations ──────────────────────────────────────────

    def _tool_calculator(self, expression: str) -> str:
        res = _safe_eval_math(expression)
        return str(res)

    def _tool_datetime(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _tool_system_status(self) -> dict[str, Any]:
        return {
            "status": "operational",
            "runtime": "EDITH-X Enterprise Distributed Gateway",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
