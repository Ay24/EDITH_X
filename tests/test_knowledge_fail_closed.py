"""Tests for Fail-Closed Vector Retrieval Policy (Point 3)."""
import pytest
from unittest.mock import MagicMock
from edith_x.core.config import Settings
from edith_x.modules.knowledge.service import KnowledgeService


@pytest.mark.asyncio
async def test_knowledge_retrieval_fail_closed_on_qdrant_error():
    settings = Settings(qdrant_host="invalid-host-unreachable.example.internal", qdrant_port=6333)
    service = KnowledgeService(settings)
    service.fail_closed = True

    # Mock client to simulate a sudden connection drop / outage during query
    mock_client = MagicMock()
    mock_client.query_points.side_effect = ConnectionError("Qdrant cluster unavailable / network partition")
    service._client = mock_client

    with pytest.raises(RuntimeError, match="Knowledge retrieval service is offline"):
        await service.retrieve("What is our Q4 policy?", org_id="org_01")

    assert service.rag_status == "DEGRADED_OFFLINE"
    assert service.is_degraded is True


@pytest.mark.asyncio
async def test_knowledge_retrieval_status_tracked_in_lenient_mode():
    settings = Settings(qdrant_host=":memory:")
    service = KnowledgeService(settings)
    service.fail_closed = False

    # Force query failure
    mock_client = MagicMock()
    mock_client.query_points.side_effect = ConnectionError("Transient network drop")
    service._client = mock_client

    # In lenient mode, should not crash, but must report degraded status
    chunks = await service.retrieve("General query", org_id="org_01")
    assert chunks == []
    assert service.rag_status == "DEGRADED_OFFLINE"
    assert service.is_degraded is True
