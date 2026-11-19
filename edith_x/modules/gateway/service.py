"""M1 — Gateway: Auth, sliding-window rate limiting, request validation."""
from __future__ import annotations

from collections import OrderedDict
import hmac
import time
import structlog

from edith_x.core.config import Settings
from edith_x.core.interfaces import AuthContext, RateLimitResult, IdentityInterface

log = structlog.get_logger(__name__)

# Default demo user for explicit demo key authentication
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
        # Bounded sliding window timestamp tracking with LRU eviction: OrderedDict[key, list[float]]
        self._request_timestamps: OrderedDict[str, list[float]] = OrderedDict()
        self._max_tracked_clients = 10000
        # Configurable plan rate limit rules: dict[plan_name, tuple[max_requests, window_seconds]]
        self._plan_limits: dict[str, tuple[int, float]] = {
            "enterprise": (1000, 60.0),
            "standard": (100, 60.0),
            "free": (20, 60.0),
        }

    def configure_rate_limit(self, plan: str, max_requests: int, window_seconds: float) -> None:
        """Dynamically configure or override sliding-window rate limits for a tenant plan."""
        self._plan_limits[plan] = (max_requests, window_seconds)

    async def authenticate(self, api_key: str) -> AuthContext | None:
        """Authenticate request using timing-safe lookup. Fail closed on invalid keys."""
        if not api_key:
            return None

        # 1. Check IdentityService registry and structured enterprise keys
        if hasattr(self._identity, "validate_key_timing_safe"):
            validated = await self._identity.validate_key_timing_safe(api_key)
            if validated:
                return validated

        # 2. Check explicit demo key only
        if api_key == "demo-key" or api_key == "demo-key-001":
            return _DEMO_AUTH

        # 3. Check static configured API key if defined
        if getattr(self._settings, "api_key", None):
            cfg_bytes = self._settings.api_key.encode("utf-8")
            cand_bytes = api_key.encode("utf-8")
            if hmac.compare_digest(cfg_bytes, cand_bytes):
                return AuthContext(
                    user_id="root-admin",
                    org_id="default-org",
                    email="admin@edith-x.ai",
                    role="admin",
                    api_key_id=api_key[:8] + "...",
                    tenant_plan="enterprise",
                )

        # 4. Strict fail-closed: forged or unrecognized keys are rejected
        return None

    async def authorize(self, ctx: AuthContext, resource: str) -> bool:
        return ctx.role in ("admin", "member")

    def prune_stale_clients(self, max_age_seconds: float | None = None) -> int:
        """Prune inactive client tracking records to ensure bounded memory footprint."""
        now = time.time()
        pruned = 0
        keys_to_del = []
        for key, timestamps in list(self._request_timestamps.items()):
            age_threshold = max_age_seconds if max_age_seconds is not None else 60.0
            if not timestamps or (now - timestamps[-1]) > age_threshold:
                keys_to_del.append(key)
        for key in keys_to_del:
            self._request_timestamps.pop(key, None)
            pruned += 1
        return pruned

    async def rate_limit(self, ctx: AuthContext) -> RateLimitResult:
        """Bounded sliding-window rate limiter per tenant/user with LRU eviction."""
        now = time.time()
        key = ctx.user_id or ctx.org_id
        max_requests, window_seconds = self._plan_limits.get(ctx.tenant_plan, (100, 60.0))

        # Evict oldest tracked client if reaching memory capacity
        if len(self._request_timestamps) >= self._max_tracked_clients and key not in self._request_timestamps:
            self._request_timestamps.popitem(last=False)

        timestamps = self._request_timestamps.get(key, [])
        cutoff = now - window_seconds
        valid_timestamps = [t for t in timestamps if t > cutoff]

        if not valid_timestamps and key in self._request_timestamps:
            self._request_timestamps.pop(key, None)

        if len(valid_timestamps) >= max_requests:
            oldest = valid_timestamps[0]
            reset_at = oldest + window_seconds
            self._request_timestamps[key] = valid_timestamps
            self._request_timestamps.move_to_end(key)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
            )

        valid_timestamps.append(now)
        self._request_timestamps[key] = valid_timestamps
        self._request_timestamps.move_to_end(key)
        remaining = max(0, max_requests - len(valid_timestamps))
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_at=now + window_seconds,
        )
