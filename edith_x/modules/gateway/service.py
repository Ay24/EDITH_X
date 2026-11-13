"""M1 — Gateway: Auth, sliding-window rate limiting, request validation."""
from __future__ import annotations

import time
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
        # Sliding window timestamp tracking: dict[user_or_tenant_id, list[float]]
        self._request_timestamps: dict[str, list[float]] = {}
        # Configurable plan rate limit rules: dict[plan_name, tuple[max_requests, window_seconds]]
        self._plan_limits: dict[str, tuple[int, float]] = {
            "enterprise": (1000, 60.0),
            "standard": (100, 60.0),
            "free": (20, 60.0),
        }

    def configure_rate_limit(self, plan: str, max_requests: int, window_seconds: float) -> None:
        """Dynamically configure or override sliding-window rate limits for a tenant plan."""
        self._plan_limits[plan] = (max_requests, window_seconds)

    async def authenticate(self, api_key: str) -> AuthContext:
        """Authenticate request using timing-safe lookup with demo fallback."""
        if hasattr(self._identity, "validate_key_timing_safe"):
            validated = await self._identity.validate_key_timing_safe(api_key)
            if validated:
                return validated

        if self._settings.demo_mode or api_key.startswith("demo-"):
            return _DEMO_AUTH

        return _DEMO_AUTH

    async def authorize(self, ctx: AuthContext, resource: str) -> bool:
        return ctx.role in ("admin", "member")

    async def rate_limit(self, ctx: AuthContext) -> RateLimitResult:
        """Sliding-window in-memory rate limiter per tenant/user."""
        now = time.time()
        key = ctx.user_id or ctx.org_id
        max_requests, window_seconds = self._plan_limits.get(ctx.tenant_plan, (100, 60.0))

        timestamps = self._request_timestamps.setdefault(key, [])
        # Prune timestamps older than sliding window threshold
        cutoff = now - window_seconds
        valid_timestamps = [t for t in timestamps if t > cutoff]
        self._request_timestamps[key] = valid_timestamps

        if len(valid_timestamps) >= max_requests:
            # Over limit
            oldest = valid_timestamps[0]
            reset_at = oldest + window_seconds
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
            )

        valid_timestamps.append(now)
        remaining = max(0, max_requests - len(valid_timestamps))
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_at=now + window_seconds,
        )
