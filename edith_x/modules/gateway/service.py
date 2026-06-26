"""M1 — Gateway: Auth, rate limiting, request validation."""
from __future__ import annotations

import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext, RateLimitResult, IdentityInterface

log = structlog.get_logger(__name__)

# Default demo user for Phase 0
_DEMO_AUTH = AuthContext(
    user_id="demo-user-001",
    org_id="demo-org-001",
    email="demo@edith-x.ai",
    role="admin",
    api_key_id="demo-key-001",
    tenant_plan="enterprise",
)


class GatewayService:
    def __init__(self, settings: Settings, identity: IdentityInterface) -> None:
        self._settings = settings
        self._identity = identity
        self._request_counts: dict[str, int] = {}

    async def authenticate(self, api_key: str) -> AuthContext:
        """Phase 0: Demo mode bypasses real auth."""
        if self._settings.demo_mode or api_key.startswith("demo-"):
            return _DEMO_AUTH
        # Phase 3: Real JWT/API key validation via Identity module
        return _DEMO_AUTH

    async def authorize(self, ctx: AuthContext, resource: str) -> bool:
        return ctx.role in ("admin", "member")

    async def rate_limit(self, ctx: AuthContext) -> RateLimitResult:
        """Phase 0: Simple in-memory counter. Phase 3: Redis-backed."""
        key = ctx.user_id
        self._request_counts[key] = self._request_counts.get(key, 0) + 1
        limit = 1000 if ctx.tenant_plan == "enterprise" else 100
        return RateLimitResult(
            allowed=self._request_counts[key] <= limit,
            remaining=max(0, limit - self._request_counts[key]),
            reset_at=0.0,
        )
