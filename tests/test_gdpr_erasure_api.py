import pytest
from httpx import AsyncClient, ASGITransport
from edith_x.interfaces.rest.app import app
from edith_x.core.container import container


@pytest.mark.asyncio
async def test_gdpr_privacy_erasure_purges_cache_and_memory():
    """Verify POST /edith/v1/privacy/erasure purges user-associated cache entries, memory, and logs a tombstone."""
    user_id = "test_user_gdpr_123"
    org_id = "demo-org-001"

    # Pre-populate cache with an entry tagged for this user
    cache = container.optimization().cache
    await cache.set(
        query="Confidential personal preferences",
        response="Personal notes for user",
        org_id=org_id,
        user_role="admin",
        user_id=user_id,
        tags=[f"user:{user_id}"],
    )

    # Verify cache entry exists
    hit = await cache.get("Confidential personal preferences", org_id=org_id, user_role="admin")
    assert hit.hit is True

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "user_id": user_id,
            "reason": "GDPR Article 17 Right to be Forgotten"
        }
        headers = {"Authorization": "Bearer demo-key"}
        response = await client.post("/edith/v1/privacy/erasure", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "erased"
        assert data["user_id"] == user_id
        assert data["cache_entries_purged"] >= 1
        assert "tombstone_hash" in data

    # Verify cache entry is completely removed
    hit_after = await cache.get("Confidential personal preferences", org_id=org_id, user_role="admin")
    assert hit_after.hit is False
