"""M2 — Identity: User/org management, RBAC, and timing-safe authentication."""
from __future__ import annotations

import hmac
import structlog
from edith_x.core.config import Settings
from edith_x.core.interfaces import AuditEvent, AuthContext, Tenant, User

log = structlog.get_logger(__name__)

_DEMO_USER = User(id="demo-user-001", org_id="demo-org-001", email="demo@edith-x.ai", role="admin")
_DEMO_TENANT = Tenant(id="demo-org-001", name="EDITH-X Demo Corp", plan="enterprise", data_residency="any")


class IdentityService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # In-memory registry of api_keys mapping to tenant/user metadata
        self._api_key_registry: dict[str, dict[str, str]] = {}

    def register_api_key(
        self,
        api_key: str,
        tenant_id: str,
        role: str = "member",
        email: str | None = None,
        plan: str = "enterprise",
    ) -> None:
        """Register an API key with constant-time lookup metadata."""
        self._api_key_registry[api_key] = {
            "tenant_id": tenant_id,
            "role": role,
            "email": email or f"user@{tenant_id}.com",
            "plan": plan,
        }

    async def validate_key_timing_safe(self, candidate_key: str) -> AuthContext | None:
        """Validate API key using constant-time comparison to prevent timing attacks."""
        candidate_bytes = candidate_key.encode("utf-8")
        matched_meta: dict[str, str] | None = None

        for reg_key, meta in self._api_key_registry.items():
            reg_bytes = reg_key.encode("utf-8")
            if hmac.compare_digest(candidate_bytes, reg_bytes):
                matched_meta = meta

        if matched_meta:
            return AuthContext(
                user_id=f"user-{matched_meta['tenant_id'][:8]}",
                org_id=matched_meta["tenant_id"],
                email=matched_meta["email"],
                role=matched_meta["role"],
                api_key_id=candidate_key[:8] + "...",
                tenant_plan=matched_meta["plan"],
            )
        return None

    async def get_user(self, api_key: str) -> User:
        return _DEMO_USER

    async def get_tenant(self, org_id: str) -> Tenant:
        return _DEMO_TENANT

    async def check_permission(self, user: User, action: str) -> bool:
        return user.role in ("admin", "member")

    async def log_audit(self, event: AuditEvent) -> None:
        log.info("audit", action=event.action, user=event.user_id, resource=event.resource)
