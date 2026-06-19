"""Bob Cloud local/CI stub routes."""

from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.application.use_cases.bob_cloud_stub_use_cases import BobCloudStubUseCases
from app.domain import StubResourceNotFound
from app.presentation.deps import get_stub_use_cases
from app.presentation.schemas import (
    CapabilityCheckRequest,
    InvitationRequest,
    LicenseUpdateRequest,
    MembershipUpdateRequest,
    TenantUpdateRequest,
)


router = APIRouter()


@router.get("/api/auth/v1/session")
async def get_session(
    response: Response,
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    payload = await use_cases.get_session()
    response.set_cookie(
        "bob_cloud_stub_session",
        payload["session_id"],
        httponly=True,
        samesite="lax",
    )
    return payload


@router.post("/api/auth/v1/refresh")
async def refresh_session(
    response: Response,
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    payload = await use_cases.refresh_session()
    response.set_cookie(
        "bob_cloud_stub_session",
        payload["session_id"],
        httponly=True,
        samesite="lax",
    )
    return payload


@router.post("/api/auth/v1/logout")
async def logout(
    response: Response,
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    response.delete_cookie("bob_cloud_stub_session")
    return await use_cases.logout()


@router.get("/api/platform/v1/entitlements/me")
async def get_entitlements(
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await use_cases.get_entitlements()


@router.post("/api/platform/v1/entitlements/check")
async def check_entitlement(
    payload: CapabilityCheckRequest,
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await use_cases.check_capability(payload.capability)


@router.get("/api/platform/v1/tenants/current")
async def get_current_tenant(
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await use_cases.get_current_tenant()


@router.get("/api/platform/v1/tenants")
async def list_tenants(
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await use_cases.list_tenants()


@router.patch("/api/platform/v1/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    payload: TenantUpdateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await _map_not_found(
        use_cases.update_tenant(
            tenant_id,
            _payload(payload),
            idempotency_key=idempotency_key,
        )
    )


@router.get("/api/platform/v1/licenses")
async def list_licenses(
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await use_cases.list_licenses()


@router.patch("/api/platform/v1/licenses/{capability}")
async def update_license(
    capability: str,
    payload: LicenseUpdateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await _map_not_found(
        use_cases.update_license(
            capability,
            _payload(payload),
            idempotency_key=idempotency_key,
        )
    )


@router.get("/api/iam/v1/users")
async def list_users(
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await use_cases.list_users()


@router.post("/api/iam/v1/invitations")
async def create_invitation(
    payload: InvitationRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await use_cases.create_invitation(
        _payload(payload),
        idempotency_key=idempotency_key,
    )


@router.get("/api/iam/v1/roles")
async def list_roles(
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await use_cases.list_roles()


@router.get("/api/iam/v1/memberships")
async def list_memberships(
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await use_cases.list_memberships()


@router.patch("/api/iam/v1/memberships/{membership_id}")
async def update_membership(
    membership_id: str,
    payload: MembershipUpdateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    use_cases: BobCloudStubUseCases = Depends(get_stub_use_cases),
) -> dict:
    return await _map_not_found(
        use_cases.update_membership(
            membership_id,
            _payload(payload),
            idempotency_key=idempotency_key,
        )
    )


async def _map_not_found(awaitable):
    try:
        return await awaitable
    except StubResourceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "stub_resource_not_found", "message": str(exc)},
        ) from exc


def _payload(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)
