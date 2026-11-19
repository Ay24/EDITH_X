"""Unit tests for Gateway security hardening and bounded rate limiter (BUG-001 & BUG-005)."""
import pytest
from edith_x.core.config import Settings
from edith_x.modules.identity.service import IdentityService
from edith_x.modules.gateway.service import GatewayService
from edith_x.core.interfaces import AuthContext


@pytest.mark.asyncio
async def test_auth_rejects_forged_and_invalid_tokens():
    settings = Settings(demo_mode=True)
    identity = IdentityService(settings)
    gateway = GatewayService(settings, identity)

    # Forged tokens must return None
    assert await gateway.authenticate("forged-evil-token") is None
    assert await gateway.authenticate("totally-invalid-token") is None
    assert await gateway.authenticate("bearer-fake-xyz") is None
    assert await gateway.authenticate("") is None


@pytest.mark.asyncio
async def test_auth_accepts_valid_demo_and_enterprise_tokens():
    settings = Settings(demo_mode=True)
    identity = IdentityService(settings)
    gateway = GatewayService(settings, identity)

    # Valid demo key
    auth_demo = await gateway.authenticate("demo-key")
    assert auth_demo is not None
    assert auth_demo.org_id == "demo-org-001"
    assert auth_demo.role == "admin"

    # Valid enterprise key: edx_live_admin_org_01
    auth_admin = await gateway.authenticate("edx_live_admin_org_01")
    assert auth_admin is not None
    assert auth_admin.org_id == "org_01"
    assert auth_admin.role == "admin"

    # Valid enterprise user key: edx_live_usr_0001_org_01
    auth_user = await gateway.authenticate("edx_live_usr_0001_org_01")
    assert auth_user is not None
    assert auth_user.org_id == "org_01"
    assert auth_user.user_id == "usr_0001"
    assert auth_user.role == "member"


@pytest.mark.asyncio
async def test_rate_limiter_memory_bounded_and_pruned():
    settings = Settings(demo_mode=True)
    identity = IdentityService(settings)
    gateway = GatewayService(settings, identity)

    # Simulate 500 unique callers with expired timestamps
    for i in range(500):
        ctx = AuthContext(
            user_id=f"transient_user_{i}",
            org_id=f"org_{i % 50}",
            email=f"user_{i}@test.com",
            role="member",
            api_key_id=f"key_{i}",
            tenant_plan="free",
        )
        res = await gateway.rate_limit(ctx)
        assert res.allowed is True

    # Check that keys are tracked
    assert len(gateway._request_timestamps) <= 500

    # Prune keys older than 0.0 seconds
    gateway.prune_stale_clients(max_age_seconds=-1.0)
    # Stale keys should be evicted
    assert len(gateway._request_timestamps) == 0
