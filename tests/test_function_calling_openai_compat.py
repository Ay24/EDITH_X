import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from edith_x.interfaces.rest.app import app


@pytest.mark.asyncio
async def test_openai_function_calling_tool_choice_returns_tool_call():
    """Verify OpenAI-compatible function calling response format when tools are provided."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": "Please generate a PDF document with title 'Financial Report' and content 'Net Profit: $1M'"}
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "generate_document",
                        "description": "Generate enterprise documents in PDF, PPTX, or XLSX",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "document_type": {"type": "string", "enum": ["pdf", "pptx", "xlsx"]},
                                "title": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["document_type", "title", "content"]
                        }
                    }
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "generate_document"}},
        }
        headers = {"Authorization": "Bearer demo-key"}
        response = await client.post("/v1/chat/completions", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert "choices" in data
        choice = data["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        message = choice["message"]
        assert message["role"] == "assistant"
        assert message["content"] is None
        assert "tool_calls" in message
        assert len(message["tool_calls"]) == 1
        
        tool_call = message["tool_calls"][0]
        assert tool_call["type"] == "function"
        assert tool_call["function"]["name"] == "generate_document"
        assert "pdf" in tool_call["function"]["arguments"].lower()


@pytest.mark.asyncio
async def test_openai_tool_loop_continuation_with_tool_response():
    """Verify that submitting a tool role message in chat history returns a synthesized assistant completion."""
    with patch("edith_x.interfaces.rest.app.container.planner") as mock_planner_provider:
        mock_planner = AsyncMock()
        mock_planner.run.return_value = {
            "run_id": "tool-loop-run",
            "final_response": "The report was generated successfully at exports/Audit.pdf.",
            "cache_hit": False,
        }
        mock_planner_provider.return_value = mock_planner

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "user", "content": "Generate a report for me."},
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc123",
                                "type": "function",
                                "function": {
                                    "name": "generate_document",
                                    "arguments": '{"document_type": "pdf", "title": "Audit", "content": "Clean"}'
                                }
                            }
                        ]
                    },
                    {
                        "role": "tool",
                        "tool_call_id": "call_abc123",
                        "name": "generate_document",
                        "content": '{"success": true, "file_path": "exports/Audit.pdf", "size_bytes": 1024}'
                    }
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "generate_document",
                            "description": "Generate enterprise documents"
                        }
                    }
                ]
            }
            headers = {"Authorization": "Bearer demo-key"}
            response = await client.post("/v1/chat/completions", json=payload, headers=headers)
            assert response.status_code == 200
            data = response.json()

            choice = data["choices"][0]
            assert choice["finish_reason"] == "stop"
            assert choice["message"]["role"] == "assistant"
            assert choice["message"]["content"] is not None
            assert "exports/Audit.pdf" in choice["message"]["content"]
