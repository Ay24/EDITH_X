"""Unit tests for constant-time auth verification and sliding-window rate limiting."""
from __future__ import annotations

import time
import pytest
from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext
from edith_x.modules.identity.service import IdentityService
from edith_x.modules.gateway.service import GatewayService


@pytest.fixture
def settings() -> Settings:
    return Settings(demo_mode=False)


@pytest.fixture
def identity_service(settings: Settings) -> IdentityService:
    return IdentityService(settings)


@pytest.fixture
def gateway_service(settings: Settings, identity_service: IdentityService) -> GatewayService:
    return GatewayService(settings, identity_service)


@pytest.mark.asyncio
async def test_constant_time_api_key_validation(identity_service: IdentityService):
    """Verify constant-time API key comparison rejects invalid keys securely."""
    # Register a test key
    identity_service.register_api_key("valid-secret-key-12345", tenant_id="tenant-alpha", role="admin")
    
    # Valid key check
    valid_res = await identity_service.validate_key_timing_safe("valid-secret-key-12345")
    assert valid_res is not None
    assert valid_res.org_id == "tenant-alpha"
    assert valid_res.role == "admin"
    
    # Invalid key check
    invalid_res = await identity_service.validate_key_timing_safe("invalid-secret-key-99999")
    assert invalid_res is None
    
    # Slightly altered key check (subtle 1 char diff)
    altered_res = await identity_service.validate_key_timing_safe("valid-secret-key-12344")
    assert altered_res is None


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter(gateway_service: GatewayService):
    """Verify that requests within a window are throttled after limit is exceeded."""
    ctx = AuthContext(
        user_id="user-burst-01",
        org_id="org-burst-01",
        email="burst@test.com",
        role="member",
        api_key_id="key-01",
        tenant_plan="standard",
    )
    
    # Standard plan limit is 5 requests per 10-second test window
    gateway_service.configure_rate_limit(plan="standard", max_requests=5, window_seconds=2)
    
    for i in range(5):
        result = await gateway_service.rate_limit(ctx)
        assert result.allowed is True
        assert result.remaining == 4 - i
        
    # 6th request in the same window must be blocked
    burst_blocked = await gateway_service.rate_limit(ctx)
    assert burst_blocked.allowed is False
    assert burst_blocked.remaining == 0
    assert burst_blocked.reset_at > time.time()
