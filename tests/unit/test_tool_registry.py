"""Unit tests for enterprise tool registry and execution engine dispatch."""
from __future__ import annotations

import pytest
from edith_x.core.config import Settings
from edith_x.core.interfaces import ToolCall
from edith_x.modules.execution.tool_registry import EnterpriseToolRegistry
from edith_x.modules.execution.service import ExecutionService


@pytest.fixture
def tool_registry() -> EnterpriseToolRegistry:
    return EnterpriseToolRegistry()


@pytest.fixture
def execution_service() -> ExecutionService:
    settings = Settings()
    return ExecutionService(settings)


@pytest.mark.asyncio
async def test_tool_registry_calculator(tool_registry: EnterpriseToolRegistry):
    call = ToolCall(id="call_01", tool="calculator", args={"expression": "100 * 1.18 + 50"})
    result = await tool_registry.execute_tool(call)
    assert result.success is True
    assert result.output == "168.0" or result.output == "168"


@pytest.mark.asyncio
async def test_tool_registry_datetime(tool_registry: EnterpriseToolRegistry):
    call = ToolCall(id="call_02", tool="datetime_now", args={})
    result = await tool_registry.execute_tool(call)
    assert result.success is True
    assert "T" in str(result.output)


@pytest.mark.asyncio
async def test_tool_registry_custom_tool(tool_registry: EnterpriseToolRegistry):
    async def mock_sql_query(query: str):
        return [{"id": 1, "status": "reconciled"}]

    tool_registry.register("sql_query", mock_sql_query, description="Execute read-only SQL query")
    call = ToolCall(id="call_03", tool="sql_query", args={"query": "SELECT * FROM transactions"})
    result = await tool_registry.execute_tool(call)
    assert result.success is True
    assert result.output == [{"id": 1, "status": "reconciled"}]


@pytest.mark.asyncio
async def test_execution_service_call_tool_dispatch(execution_service: ExecutionService):
    call = ToolCall(id="call_04", tool="calculator", args={"expression": "500 / 2"})
    result = await execution_service.call_tool(call)
    assert result.success is True
    assert float(result.output) == 250.0


@pytest.mark.asyncio
async def test_unregistered_tool_returns_error(execution_service: ExecutionService):
    call = ToolCall(id="call_05", tool="non_existent_tool", args={})
    result = await execution_service.call_tool(call)
    assert result.success is False
    assert "Unregistered tool" in result.error
