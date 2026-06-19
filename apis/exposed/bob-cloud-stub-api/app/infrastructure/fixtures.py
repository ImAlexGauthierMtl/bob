"""Deterministic Bob Cloud fixtures for local and CI runs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from app.domain import StubResourceNotFound


TENANT_ID = "tenant-croo-local"
USER_ID = "user-alex-local"
SESSION_ID = "sess-bob-cloud-stub"

TENANT = {
    "id": TENANT_ID,
    "name": "Croo Local",
    "status": "active",
    "hierarchy_path": "/croo-local",
    "scope": "tenant_self",
}

USER = {
    "id": USER_ID,
    "email": "alexandre.local@croo.digital",
    "display_name": "Alexandre Local",
    "status": "active",
}

ROLES = [
    {"id": "role-admin", "code": "admin", "label": "Admin"},
    {"id": "role-support", "code": "support", "label": "Support"},
]

MEMBERSHIPS = [
    {
        "id": "membership-local-admin",
        "tenant_id": TENANT_ID,
        "user_id": USER_ID,
        "role_codes": ["admin", "support"],
        "status": "active",
    }
]

CAPABILITIES = {
    "bob_chat.use": {"status": "enabled", "remaining": 100, "limit": 100},
    "bob_cockpit.use": {"status": "enabled", "remaining": 100, "limit": 100},
    "agent.run.create": {"status": "enabled", "remaining": 50, "limit": 50},
    "agent_memory.use": {"status": "enabled", "remaining": 100, "limit": 100},
    "agent_memory.vector.manage": {"status": "enabled", "remaining": 10, "limit": 10},
    "agent.voice.customer_experience": {"status": "disabled", "remaining": 0, "limit": 0},
}


class BobCloudFixtureSource:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.tenants = [deepcopy(TENANT)]
        self.users = [deepcopy(USER)]
        self.roles = deepcopy(ROLES)
        self.memberships = deepcopy(MEMBERSHIPS)
        self.capabilities = deepcopy(CAPABILITIES)
        self._invitations_by_key: dict[str, dict[str, Any]] = {}
        self._tenant_updates_by_key: dict[str, dict[str, Any]] = {}
        self._license_updates_by_key: dict[str, dict[str, Any]] = {}
        self._membership_updates_by_key: dict[str, dict[str, Any]] = {}

    def session_payload(self) -> dict[str, Any]:
        user = self.users[0]
        tenant = self.tenants[0]
        return {
            "authenticated": True,
            "session_id": SESSION_ID,
            "user": deepcopy(user),
            "tenant": deepcopy(tenant),
            "permissions": sorted(self.capabilities.keys()),
            "platform_roles": ["admin", "support"],
            "expires_at": "2099-01-01T00:00:00Z",
            "source": "bob-cloud-stub",
        }

    def entitlements_payload(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenants[0]["id"],
            "user_id": self.users[0]["id"],
            "module_entitlements": self._module_entitlements(),
            "capabilities": [
                {"code": code, "source": "stub-license", **data}
                for code, data in sorted(self.capabilities.items())
            ],
        }

    def get_capability(self, capability: str) -> Optional[dict[str, Any]]:
        capability_payload = self.capabilities.get(capability)
        return deepcopy(capability_payload) if capability_payload else None

    def tenant_payload(self) -> dict[str, Any]:
        return deepcopy(self.tenants[0])

    def tenants_payload(self) -> dict[str, Any]:
        return {"items": deepcopy(self.tenants), "source": "bob-cloud-stub"}

    def update_tenant(
        self,
        tenant_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if idempotency_key in self._tenant_updates_by_key:
            return deepcopy(self._tenant_updates_by_key[idempotency_key])

        tenant = self._find_tenant(tenant_id)
        for field in ("name", "status", "hierarchy_path", "scope"):
            if field in payload and payload[field] is not None:
                tenant[field] = payload[field]

        result = {"source": "bob-cloud-stub", **deepcopy(tenant)}
        self._tenant_updates_by_key[idempotency_key] = result
        return deepcopy(result)

    def licenses_payload(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenants[0]["id"],
            "items": [
                {"code": code, "source": "stub-license", **data}
                for code, data in sorted(self.capabilities.items())
            ],
            "module_entitlements": self._module_entitlements(),
            "source": "bob-cloud-stub",
        }

    def update_license(
        self,
        capability: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if idempotency_key in self._license_updates_by_key:
            return deepcopy(self._license_updates_by_key[idempotency_key])

        if capability not in self.capabilities:
            raise StubResourceNotFound(f"license_not_found:{capability}")

        capability_payload = self.capabilities[capability]
        for field in ("status", "remaining", "limit"):
            if field in payload and payload[field] is not None:
                capability_payload[field] = payload[field]

        result = {"code": capability, "source": "stub-license", **deepcopy(capability_payload)}
        self._license_updates_by_key[idempotency_key] = result
        return deepcopy(result)

    def create_invitation(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if idempotency_key in self._invitations_by_key:
            return deepcopy(self._invitations_by_key[idempotency_key])

        email = str(payload["email"])
        display_name = payload.get("display_name") or email.split("@")[0]
        role_codes = payload.get("role_codes") or ["support"]
        tenant_id = payload.get("tenant_id") or self.tenants[0]["id"]
        user_id = f"user-local-{len(self.users) + 1}"
        invitation_id = f"invite-local-{len(self._invitations_by_key) + 1}"
        membership_id = f"membership-local-{len(self.memberships) + 1}"

        user = {
            "id": user_id,
            "email": email,
            "display_name": display_name,
            "status": "invited",
        }
        membership = {
            "id": membership_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "role_codes": list(role_codes),
            "status": "pending",
        }
        self.users.append(user)
        self.memberships.append(membership)

        invitation = {
            "id": invitation_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "membership_id": membership_id,
            "email": email,
            "display_name": display_name,
            "role_codes": list(role_codes),
            "status": "pending",
            "source": "bob-cloud-stub",
        }
        self._invitations_by_key[idempotency_key] = invitation
        return deepcopy(invitation)

    def roles_payload(self) -> list[dict[str, Any]]:
        return deepcopy(self.roles)

    def memberships_payload(self) -> list[dict[str, Any]]:
        return deepcopy(self.memberships)

    def users_payload(self) -> list[dict[str, Any]]:
        return deepcopy(self.users)

    def update_membership(
        self,
        membership_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if idempotency_key in self._membership_updates_by_key:
            return deepcopy(self._membership_updates_by_key[idempotency_key])

        membership = self._find_membership(membership_id)
        if "role_codes" in payload and payload["role_codes"] is not None:
            membership["role_codes"] = list(payload["role_codes"])
        if "status" in payload and payload["status"] is not None:
            membership["status"] = payload["status"]

        result = {"source": "bob-cloud-stub", **deepcopy(membership)}
        self._membership_updates_by_key[idempotency_key] = result
        return deepcopy(result)

    def _find_tenant(self, tenant_id: str) -> dict[str, Any]:
        for tenant in self.tenants:
            if tenant["id"] == tenant_id:
                return tenant
        raise StubResourceNotFound(f"tenant_not_found:{tenant_id}")

    def _find_membership(self, membership_id: str) -> dict[str, Any]:
        for membership in self.memberships:
            if membership["id"] == membership_id:
                return membership
        raise StubResourceNotFound(f"membership_not_found:{membership_id}")

    def _module_entitlements(self) -> dict[str, str]:
        return {
            "bob_chat": self.capabilities["bob_chat.use"]["status"],
            "bob_cockpit": self.capabilities["bob_cockpit.use"]["status"],
            "agent_memory": self.capabilities["agent_memory.use"]["status"],
            "customer_experience_agent": self.capabilities[
                "agent.voice.customer_experience"
            ]["status"],
            "go_shell": "preview",
        }
