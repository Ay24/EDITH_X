import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from edith_x.interfaces.rest.app import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/edith/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "providers" in data

def test_prometheus_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "edith_requests_total" in response.text

def test_openai_chat_completions_and_caching():
    mock_resp = AsyncMock()
    mock_resp.choices = [AsyncMock(message=AsyncMock(content="Paris is the capital of France."))]
    mock_resp.usage = AsyncMock(prompt_tokens=15, completion_tokens=8)

    with patch("litellm.acompletion", return_value=mock_resp):
        payload = {
            "model": "edith-x-auto",
            "messages": [{"role": "user", "content": "What is the capital of France?"}]
        }

        # 1. First Call: Compute / Execution path
        resp1 = client.post("/v1/chat/completions", json=payload, headers={"Authorization": "Bearer demo-key"})
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["object"] == "chat.completion"
        assert "Paris" in data1["choices"][0]["message"]["content"]
        assert "edith_metadata" in data1
        assert data1["edith_metadata"]["cache_hit"] is False

        # 2. Second Call: Cache Hit path
        resp2 = client.post("/v1/chat/completions", json=payload, headers={"Authorization": "Bearer demo-key"})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert "Paris" in data2["choices"][0]["message"]["content"]
        assert data2["edith_metadata"]["cache_hit"] is True
        assert data2["edith_metadata"]["cost_usd"] == 0.0

def test_autonomous_goal_run():
    mock_resp = AsyncMock()
    mock_resp.choices = [AsyncMock(message=AsyncMock(content="Autonomous plan completed successfully."))]
    mock_resp.usage = AsyncMock(prompt_tokens=25, completion_tokens=12)

    with patch("litellm.acompletion", return_value=mock_resp):
        payload = {"goal": "Audit current enterprise security configurations"}
        response = client.post("/edith/v1/run", json=payload, headers={"Authorization": "Bearer demo-key"})
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "Autonomous plan completed successfully." in data["response"]
        assert "model" in data
