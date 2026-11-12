"""Unit tests for Qdrant-backed hybrid retrieval KnowledgeService and MemoryService."""
import pytest
from edith_x.core.config import Settings
from edith_x.core.interfaces import Document
from edith_x.modules.knowledge.service import KnowledgeService
from edith_x.modules.memory.service import MemoryService


@pytest.fixture
def settings():
    return Settings(
        qdrant_host=":memory:",  # In-memory Qdrant
        demo_mode=True,
    )


@pytest.mark.asyncio
async def test_knowledge_index_and_hybrid_retrieve(settings):
    svc = KnowledgeService(settings)
    doc = Document(
        id="doc_ai_policy",
        content="Enterprise AI policy requires strict PII redaction and local execution for sensitive banking records. Cloud execution is restricted.",
        source="compliance_handbook",
        metadata={"category": "compliance"},
    )
    doc_id = await svc.index(doc, source="compliance_handbook")
    assert doc_id == "doc_ai_policy"

    # Query matching semantic concept and keywords
    chunks = await svc.retrieve("What is the policy for banking records and PII redaction?", top_k=3)
    assert len(chunks) >= 1
    assert "banking records" in chunks[0].content
    assert chunks[0].score > 0.0
    assert chunks[0].source == "compliance_handbook"


@pytest.mark.asyncio
async def test_knowledge_source_filtering(settings):
    svc = KnowledgeService(settings)
    await svc.index(
        Document(id="doc_tech", content="Python 3.12 introduces improved performance and sys.monitoring.", source="tech_docs"),
        source="tech_docs",
    )
    await svc.index(
        Document(id="doc_hr", content="Annual leave policy allows 25 days of paid time off.", source="hr_portal"),
        source="hr_portal",
    )

    # Filter only by hr_portal
    hr_chunks = await svc.retrieve("leave policy", sources=["hr_portal"], top_k=5)
    assert all(c.source == "hr_portal" for c in hr_chunks)

    # Filter only by tech_docs
    tech_chunks = await svc.retrieve("leave policy", sources=["tech_docs"], top_k=5)
    assert len(tech_chunks) == 0


@pytest.mark.asyncio
async def test_memory_store_and_retrieve(settings):
    svc = MemoryService(settings)
    await svc.store("user_alpha", "User prefers concise answers with typescript code examples.", scope="user")
    await svc.store("user_beta", "User is interested in Python data science libraries.", scope="user")

    # Retrieve for user_alpha
    alpha_mem = await svc.get("user_alpha", "typescript coding preference", top_k=2)
    assert len(alpha_mem) >= 1
    assert "typescript" in alpha_mem[0].content

    # Forget memory
    mem_id = alpha_mem[0].id
    await svc.forget("user_alpha", mem_id)
    alpha_mem_after = await svc.get("user_alpha", "typescript", top_k=2)
    assert len(alpha_mem_after) == 0
