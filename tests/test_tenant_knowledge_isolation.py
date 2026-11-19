"""Unit test for multi-tenant knowledge retrieval isolation in Planner graph (BUG-003)."""
import pytest
from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext, Document
from edith_x.modules.knowledge.service import KnowledgeService
from edith_x.modules.planner.service import PlannerService
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_planner_node_retrieve_enforces_org_id_isolation():
    settings = Settings(demo_mode=True)
    knowledge = KnowledgeService(settings)

    # Seed Tenant A's private document with canary
    doc_a = Document(
        content="Secret revenue figures for Alpha: CANARY-org_alpha-9988",
        source="internal_docs",
        metadata={"org_id": "org_alpha"},
    )
    await knowledge.index(doc_a)

    # Seed Tenant B's private document with canary
    doc_b = Document(
        content="Beta cloud security architecture: CANARY-org_beta-1122",
        source="internal_docs",
        metadata={"org_id": "org_beta"},
    )
    await knowledge.index(doc_b)

    # Initialize PlannerService
    mock_obs = AsyncMock()
    planner = PlannerService(
        settings=settings,
        knowledge=knowledge,
        context=AsyncMock(),
        optimization=AsyncMock(),
        router=AsyncMock(),
        execution=AsyncMock(),
        verification=AsyncMock(),
        reflection=AsyncMock(),
        memory=AsyncMock(),
        observability=mock_obs,
    )

    # State for Tenant B asking about Alpha's document
    auth_b = AuthContext(
        user_id="usr_beta_01",
        org_id="org_beta",
        email="beta@org_beta.com",
        role="member",
        api_key_id="key_beta",
        tenant_plan="enterprise",
    )
    state_b = {
        "goal": "Retrieve Alpha secret revenue CANARY-org_alpha-9988",
        "user_id": auth_b.user_id,
        "auth": auth_b,
    }

    # Execute _node_retrieve for Tenant B
    retrieved_state = await planner._node_retrieve(state_b)
    chunks = retrieved_state.get("knowledge_chunks", [])
    chunk_contents = " ".join(c.get("content", "") for c in chunks)

    # Tenant B must NOT retrieve Tenant A's document or canary
    assert "CANARY-org_alpha-9988" not in chunk_contents
