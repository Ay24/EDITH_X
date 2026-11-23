"""Tests for Native SSE Streaming with Live Output Redaction (Priority 2)."""
import json
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from edith_x.interfaces.rest.app import app


@pytest.mark.asyncio
async def test_native_sse_streaming_endpoint():
    with patch("edith_x.interfaces.rest.app.container.planner") as mock_planner_provider:
        mock_planner = AsyncMock()
        mock_planner.run.return_value = {
            "run_id": "test-stream-1",
            "final_response": "Hello world, streaming response active.",
            "cache_hit": False,
        }
        mock_planner_provider.return_value = mock_planner

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Say hello"}],
                "stream": True,
            }
            headers = {"Authorization": "Bearer demo-key"}
            response = await client.post("/v1/chat/completions", json=payload, headers=headers)
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            content = response.text
            assert "data: " in content
            assert "[DONE]" in content


@pytest.mark.asyncio
async def test_streaming_live_redaction_prevents_secret_leakage():
    with patch("edith_x.interfaces.rest.app.container.planner") as mock_planner_provider:
        mock_planner = AsyncMock()
        # Leaked credentials in model stream
        mock_planner.run.return_value = {
            "run_id": "test-stream-2",
            "final_response": "The customer card is 4532 0150 1234 5678 and key: sec_mock_leaked_key_1234567890abcdef",
            "cache_hit": False,
        }
        mock_planner_provider.return_value = mock_planner

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Retrieve account"}],
                "stream": True,
            }
            headers = {"Authorization": "Bearer demo-key"}
            response = await client.post("/v1/chat/completions", json=payload, headers=headers)
            assert response.status_code == 200
            body = response.text

            # Stream must not leak the raw card or secret
            assert "4532 0150 1234 5678" not in body
            assert "[REDACTED_CREDIT_CARD]" in body
            assert "sec_mock_leaked_key_1234567890abcdef" not in body
            assert "[REDACTED_SECRET]" in body
