"""M2 — Identity: User/org management, RBAC stubs for Phase 0."""
from __future__ import annotations
import structlog
from edith_x.core.config import Settings
from edith_x.core.interfaces import AuditEvent, Tenant, User

log = structlog.get_logger(__name__)

_DEMO_USER = User(id="demo-user-001", org_id="demo-org-001", email="demo@edith-x.ai", role="admin")
_DEMO_TENANT = Tenant(id="demo-org-001", name="EDITH-X Demo Corp", plan="enterprise", data_residency="any")


class IdentityService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_user(self, api_key: str) -> User:
        return _DEMO_USER

    async def get_tenant(self, org_id: str) -> Tenant:
        return _DEMO_TENANT

    async def check_permission(self, user: User, action: str) -> bool:
        return user.role in ("admin", "member")

    async def log_audit(self, event: AuditEvent) -> None:
        log.info("audit", action=event.action, user=event.user_id, resource=event.resource)
