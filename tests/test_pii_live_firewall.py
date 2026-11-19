"""Unit tests for live PII/secret redaction in API endpoints (BUG-002)."""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from edith_x.interfaces.rest.app import app


@pytest.mark.asyncio
async def test_run_endpoint_redacts_card_numbers_and_secrets():
    with patch("edith_x.interfaces.rest.app.container.planner") as mock_planner_provider:
        mock_planner = AsyncMock()
        mock_planner.run.return_value = {
            "run_id": "test-run-123",
            "final_response": "Processed successfully",
            "cache_hit": False,
        }
        mock_planner_provider.return_value = mock_planner

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "goal": "Pay vendor $50 using card 4532 0150 1234 5678 and key: sec_mock_test_token_8a7b6c5d4e3f2a1b0c9d8e7f"
            }
            headers = {"Authorization": "Bearer demo-key"}
            response = await client.post("/edith/v1/run", json=payload, headers=headers)
            assert response.status_code == 200

            # Verify that planner.run was called with sanitized text
            called_goal = mock_planner.run.call_args[0][0]
            assert "4532 0150 1234 5678" not in called_goal
            assert "[REDACTED_CREDIT_CARD]" in called_goal
            assert "sec_mock_test_token_8a7b6c5d4e3f2a1b0c9d8e7f" not in called_goal
            assert "[REDACTED_SECRET]" in called_goal


@pytest.mark.asyncio
async def test_chat_completions_redacts_card_numbers_and_secrets():
    with patch("edith_x.interfaces.rest.app.container.planner") as mock_planner_provider:
        mock_planner = AsyncMock()
        mock_planner.run.return_value = {
            "run_id": "test-chat-123",
            "final_response": "Processed transaction",
            "cache_hit": False,
        }
        mock_planner_provider.return_value = mock_planner

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "messages": [
                    {"role": "user", "content": "My SSN is 123-45-6789, verify my account."}
                ]
            }
            headers = {"Authorization": "Bearer demo-key"}
            response = await client.post("/v1/chat/completions", json=payload, headers=headers)
            assert response.status_code == 200

            called_goal = mock_planner.run.call_args[0][0]
            assert "123-45-6789" not in called_goal
            assert "[REDACTED_SSN]" in called_goal
