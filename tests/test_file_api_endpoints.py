import io
import pytest
from httpx import AsyncClient, ASGITransport
from edith_x.interfaces.rest.app import app


@pytest.mark.asyncio
async def test_openai_compatible_files_upload():
    """Verify POST /v1/files accepts multipart file upload and returns OpenAI-compatible File object."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        file_content = b"This is a confidential quarterly report for Acme Corp. All rights reserved."
        files = {
            "file": ("quarterly_report.txt", io.BytesIO(file_content), "text/plain")
        }
        data = {"purpose": "assistants"}
        headers = {"Authorization": "Bearer demo-key"}

        response = await client.post("/v1/files", files=files, data=data, headers=headers)
        assert response.status_code == 200
        result = response.json()

        assert result["object"] == "file"
        assert result["filename"] == "quarterly_report.txt"
        assert result["purpose"] == "assistants"
        assert result["bytes"] == len(file_content)
        assert result["id"].startswith("file-")


@pytest.mark.asyncio
async def test_file_summarize_endpoint_with_caching():
    """Verify POST /edith/v1/files/summarize runs hierarchical summary and caches repeat calls ($0 repeat cost)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First upload a file
        file_content = b"Section 1: Revenue was $5M in Q1. Section 2: Operating expenses were $3M. Section 3: Net profit was $2M."
        files = {
            "file": ("financials.txt", io.BytesIO(file_content), "text/plain")
        }
        headers = {"Authorization": "Bearer demo-key"}
        upload_resp = await client.post("/v1/files", files=files, data={"purpose": "assistants"}, headers=headers)
        assert upload_resp.status_code == 200
        file_id = upload_resp.json()["id"]

        # Call summarize endpoint
        sum_payload = {
            "file_id": file_id,
            "prompt": "Summarize net profit"
        }
        resp1 = await client.post("/edith/v1/files/summarize", json=sum_payload, headers=headers)
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert "summary" in data1
        assert data1["chunks_processed"] >= 1
        assert data1["cache_hit"] is False

        # Repeat summary request with identical file and prompt -> Cache Hit ($0 cost)
        resp2 = await client.post("/edith/v1/files/summarize", json=sum_payload, headers=headers)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["cache_hit"] is True
        assert data2["cost_usd"] == 0.0
