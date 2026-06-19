"""Bob Cloud local stub use cases."""

from __future__ import annotations

from typing import Any, Optional, Protocol

from app.domain import CapabilityDecision


class BobCloudFixturePort(Protocol):
    def session_payload(self) -> dict[str, Any]:
        ...

    def entitlements_payload(self) -> dict[str, Any]:
        ...

    def get_capability(self, capability: str) -> Optional[dict[str, Any]]:
        ...

    def tenant_payload(self) -> dict[str, Any]:
        ...

    def tenants_payload(self) -> dict[str, Any]:
        ...

    def update_tenant(
        self,
        tenant_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        ...

    def licenses_payload(self) -> dict[str, Any]:
        ...

    def update_license(
        self,
        capability: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        ...

    def users_payload(self) -> list[dict[str, Any]]:
        ...

    def create_invitation(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        ...

    def roles_payload(self) -> list[dict[str, Any]]:
        ...

    def memberships_payload(self) -> list[dict[str, Any]]:
        ...

    def update_membership(
        self,
        membership_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        ...


class BobCloudStubUseCases:
    def __init__(self, *, fixtures: BobCloudFixturePort) -> None:
        self.fixtures = fixtures

    async def get_session(self) -> dict[str, Any]:
        return self.fixtures.session_payload()

    async def refresh_session(self) -> dict[str, Any]:
        return self.fixtures.session_payload()

    async def logout(self) -> dict[str, Any]:
        return {"authenticated": False, "source": "bob-cloud-stub"}

    async def get_entitlements(self) -> dict[str, Any]:
        return self.fixtures.entitlements_payload()

    async def check_capability(self, capability: str) -> dict[str, Any]:
        capability_payload = self.fixtures.get_capability(capability)
        if not capability_payload:
            return CapabilityDecision(
                capability=capability,
                status="denied",
                reason_code="capability_unknown",
            ).to_payload()
        return CapabilityDecision(capability=capability, **capability_payload).to_payload()

    async def get_current_tenant(self) -> dict[str, Any]:
        return self.fixtures.tenant_payload()

    async def list_tenants(self) -> dict[str, Any]:
        return self.fixtures.tenants_payload()

    async def update_tenant(
        self,
        tenant_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self.fixtures.update_tenant(
            tenant_id,
            payload,
            idempotency_key=idempotency_key,
        )

    async def list_licenses(self) -> dict[str, Any]:
        return self.fixtures.licenses_payload()

    async def update_license(
        self,
        capability: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self.fixtures.update_license(
            capability,
            payload,
            idempotency_key=idempotency_key,
        )

    async def list_users(self) -> dict[str, Any]:
        return {"items": self.fixtures.users_payload(), "source": "bob-cloud-stub"}

    async def create_invitation(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self.fixtures.create_invitation(
            payload,
            idempotency_key=idempotency_key,
        )

    async def list_roles(self) -> dict[str, Any]:
        return {"items": self.fixtures.roles_payload(), "source": "bob-cloud-stub"}

    async def list_memberships(self) -> dict[str, Any]:
        return {"items": self.fixtures.memberships_payload(), "source": "bob-cloud-stub"}

    async def update_membership(
        self,
        membership_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self.fixtures.update_membership(
            membership_id,
            payload,
            idempotency_key=idempotency_key,
        )
