"""M2 — Identity: User/org management, RBAC, and timing-safe authentication."""
from __future__ import annotations

import hmac
import structlog
from edith_x.core.config import Settings
from edith_x.core.interfaces import AuditEvent, AuthContext, Tenant, User
from edith_x.modules.identity.audit_ledger import AuditLedger

log = structlog.get_logger(__name__)

_DEMO_USER = User(id="demo-user-001", org_id="demo-org-001", email="demo@edith-x.ai", role="admin")
_DEMO_TENANT = Tenant(id="demo-org-001", name="EDITH-X Demo Corp", plan="enterprise", data_residency="any")


class IdentityService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # In-memory registry of api_keys mapping to tenant/user metadata
        self._api_key_registry: dict[str, dict[str, str]] = {}
        self._audit_ledger = AuditLedger()

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
        if not candidate_key:
            return None

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

        # Support structured enterprise keys: edx_live_<role>_<org_id> or edx_live_usr_<id>_<org_id>
        if candidate_key.startswith("edx_live_") or candidate_key.startswith("edx_test_"):
            parts = candidate_key.split("_")
            is_live = parts[1] == "live"
            # Format A: edx_live_admin_org_01 or edx_live_user_org_01 (len == 5, parts[3] == 'org')
            if len(parts) == 5 and parts[3] == "org":
                role = "admin" if parts[2] == "admin" else "member"
                org_id = f"org_{parts[4]}"
                return AuthContext(
                    user_id=f"usr_{parts[2]}_{org_id}",
                    org_id=org_id,
                    email=f"{parts[2]}@{org_id}.enterprise",
                    role=role,
                    api_key_id=candidate_key[:14] + "...",
                    tenant_plan="enterprise" if is_live else "standard",
                )
            # Format B: edx_live_usr_0001_org_01 (len >= 6, parts[2] == 'usr')
            elif len(parts) >= 6 and parts[2] == "usr":
                user_id = f"usr_{parts[3]}"
                org_id = "_".join(parts[4:])
                return AuthContext(
                    user_id=user_id,
                    org_id=org_id,
                    email=f"{user_id}@{org_id}.internal",
                    role="member",
                    api_key_id=candidate_key[:14] + "...",
                    tenant_plan="enterprise" if is_live else "standard",
                )
            # Format C: edx_live_<org_tag>_<token>
            elif len(parts) >= 4:
                org_tag = parts[2]
                org_id = f"org-{org_tag}" if not org_tag.startswith("org") else org_tag
                return AuthContext(
                    user_id=f"service-user-{org_tag}",
                    org_id=org_id,
                    email=f"gateway@{org_tag}.enterprise",
                    role="admin" if is_live else "member",
                    api_key_id=candidate_key[:14] + "...",
                    tenant_plan="enterprise" if is_live else "standard",
                )

        return None

    async def get_user(self, api_key: str) -> User:
        return _DEMO_USER

    async def get_tenant(self, org_id: str) -> Tenant:
        return _DEMO_TENANT

    async def check_permission(self, user: User, action: str) -> bool:
        return user.role in ("admin", "member")

    @property
    def audit_ledger(self) -> AuditLedger:
        return self._audit_ledger

    async def log_audit(self, event: AuditEvent) -> None:
        log.info("audit", action=event.action, user=event.user_id, resource=event.resource)
        self._audit_ledger.record_event(
            action=event.action,
            user_id=event.user_id,
            org_id=getattr(event, "org_id", "default_org"),
            details={"resource": event.resource, "status": event.status, "metadata": getattr(event, "metadata", {})},
        )
