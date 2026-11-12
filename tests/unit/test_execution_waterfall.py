import pytest
from unittest.mock import AsyncMock, patch
from edith_x.core.config import Settings
from edith_x.core.interfaces import Context, ModelSelection
from edith_x.modules.execution.service import ExecutionService

@pytest.mark.asyncio
async def test_fallback_when_primary_provider_fails():
    settings = Settings(openai_api_key="test-key", nvidia_api_key="test-key")
    svc = ExecutionService(settings)
    ctx = Context(query="Summarize this text")
    primary_selection = ModelSelection(
        provider="nvidia_nim",
        model="meta/llama-3.1-70b-instruct",
        reasoning="Primary cloud model"
    )

    mock_resp = AsyncMock()
    mock_resp.choices = [AsyncMock(message=AsyncMock(content="Fallback response from OpenAI"))]
    mock_resp.usage = AsyncMock(prompt_tokens=10, completion_tokens=15)

    with patch("litellm.acompletion") as mock_comp:
        from litellm.exceptions import NotFoundError
        mock_comp.side_effect = [
            NotFoundError(message="Model not found 404", model="nvidia_nim", llm_provider="nvidia_nim"),
            mock_resp
        ]

        result = await svc.execute(ctx, primary_selection)
        assert result.response == "Fallback response from OpenAI"
        assert result.failover_active is True
        assert "404" in result.failover_reason or "not found" in result.failover_reason.lower()

@pytest.mark.asyncio
async def test_primary_succeeds_without_fallback():
    settings = Settings(openai_api_key="test-key")
    svc = ExecutionService(settings)
    ctx = Context(query="Hello")
    primary_selection = ModelSelection(
        provider="openai",
        model="gpt-4o-mini",
        reasoning="Direct call"
    )

    mock_resp = AsyncMock()
    mock_resp.choices = [AsyncMock(message=AsyncMock(content="Hello there!"))]
    mock_resp.usage = AsyncMock(prompt_tokens=5, completion_tokens=5)

    with patch("litellm.acompletion", return_value=mock_resp):
        result = await svc.execute(ctx, primary_selection)
        assert result.response == "Hello there!"
        assert result.failover_active is False
