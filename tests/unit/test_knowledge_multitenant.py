"""Unit tests for multi-tenant isolation in Qdrant knowledge vector search."""
from __future__ import annotations

import pytest
from edith_x.core.config import Settings
from edith_x.core.interfaces import Document
from edith_x.modules.knowledge.service import KnowledgeService


@pytest.fixture
def knowledge_service() -> KnowledgeService:
    settings = Settings(qdrant_host=":memory:")
    return KnowledgeService(settings)


@pytest.mark.asyncio
async def test_tenant_isolation_in_retrieval(knowledge_service: KnowledgeService):
    # Ingest document for Tenant Alpha
    doc_alpha = Document(
        id="doc_alpha_01",
        content="Tenant Alpha proprietary revenue formula: NetRevenue = Gross - (Discounts * 1.5).",
        source="alpha_policy.txt",
        metadata={"org_id": "org_alpha", "classification": "confidential"},
    )
    await knowledge_service.ingest(doc_alpha)

    # Ingest document for Tenant Beta
    doc_beta = Document(
        id="doc_beta_01",
        content="Tenant Beta secret customer list includes GlobalCorp, MegaFirm, and FinGroup.",
        source="beta_policy.txt",
        metadata={"org_id": "org_beta", "classification": "restricted"},
    )
    await knowledge_service.ingest(doc_beta)

    # Tenant Alpha queries about customer lists
    results_alpha = await knowledge_service.retrieve(
        query="What customer companies are listed?",
        org_id="org_alpha",
    )
    # Must NOT return Tenant Beta's document
    for chunk in results_alpha:
        assert "GlobalCorp" not in chunk.content
        assert "MegaFirm" not in chunk.content

    # Tenant Beta queries about revenue formula
    results_beta = await knowledge_service.retrieve(
        query="What is the net revenue formula?",
        org_id="org_beta",
    )
    # Must NOT return Tenant Alpha's document
    for chunk in results_beta:
        assert "Discounts * 1.5" not in chunk.content

    # Query without org_id filter returns matched content
    results_all = await knowledge_service.retrieve(query="revenue formula")
    assert any("Discounts * 1.5" in chunk.content for chunk in results_all)
