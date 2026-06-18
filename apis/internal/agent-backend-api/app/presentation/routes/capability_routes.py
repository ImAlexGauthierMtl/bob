"""Capability routes — CRUD for capability definitions and user capability assignments."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.models.capability import CapabilityDefinition, UserCapability, DeptCapability
from app.infrastructure.persistence.models.department import UserDepartment
from app.presentation.schemas.capability_schemas import (
    CapabilityDefinitionResponse,
    UserCapabilityAssign,
    UserCapabilityResponse,
    UserCapabilitiesResponse,
)

router = APIRouter(prefix="/api/v1/capabilities")


def _get_user_trust(db: Session, user_id: str) -> float:
    """Cross-service query to get user trust_score."""
    result = db.execute(text("SELECT trust_score FROM users WHERE id = :uid"), {"uid": user_id}).first()
    return result[0] if result else 0.0


def _resolve_capability(db: Session, user_id: str, cap_def: CapabilityDefinition, tenant_id: str) -> tuple[bool, str]:
    """Resolve if capability is granted and its source."""
    user_override = db.query(UserCapability).filter(
        UserCapability.user_id == user_id,
        UserCapability.capability_id == cap_def.id,
        UserCapability.tenant_id == tenant_id,
    ).first()
    if user_override:
        return user_override.granted, "user"

    user_dept_ids = [
        ud.department_id for ud in
        db.query(UserDepartment).filter(UserDepartment.user_id == user_id).all()
    ]
    if user_dept_ids:
        dept_caps = db.query(DeptCapability).filter(
            DeptCapability.department_id.in_(user_dept_ids),
            DeptCapability.capability_id == cap_def.id,
            DeptCapability.tenant_id == tenant_id,
        ).all()
        if dept_caps:
            return any(dc.granted for dc in dept_caps), "department"

    return cap_def.default_enabled, "system"


@router.get("/catalog", response_model=list[CapabilityDefinitionResponse])
async def list_capability_catalog(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(CapabilityDefinition).order_by(
        CapabilityDefinition.scope,
        CapabilityDefinition.code,
    ).all()


@router.get("/users/{user_id}", response_model=UserCapabilitiesResponse)
async def get_user_capabilities(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    all_defs = db.query(CapabilityDefinition).order_by(
        CapabilityDefinition.scope, CapabilityDefinition.code,
    ).all()
    trust_score = _get_user_trust(db, user_id)

    caps = []
    for cap_def in all_defs:
        granted, source = _resolve_capability(db, user_id, cap_def, current_user["tenant_id"])
        caps.append(UserCapabilityResponse(
            code=cap_def.code, name=cap_def.name, scope=cap_def.scope,
            module=cap_def.module, risk_level=cap_def.risk_level,
            granted=granted, source=source,
        ))

    return UserCapabilitiesResponse(
        user_id=user_id, agent_mode="standard",
        trust_score=trust_score, capabilities=caps,
    )


@router.get("/me", response_model=UserCapabilitiesResponse)
async def get_my_capabilities(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["user_id"]
    all_defs = db.query(CapabilityDefinition).order_by(
        CapabilityDefinition.scope, CapabilityDefinition.code,
    ).all()
    trust_score = _get_user_trust(db, user_id)

    caps = []
    for cap_def in all_defs:
        granted, source = _resolve_capability(db, user_id, cap_def, current_user["tenant_id"])
        caps.append(UserCapabilityResponse(
            code=cap_def.code, name=cap_def.name, scope=cap_def.scope,
            module=cap_def.module, risk_level=cap_def.risk_level,
            granted=granted, source=source,
        ))

    return UserCapabilitiesResponse(
        user_id=user_id, agent_mode="standard",
        trust_score=trust_score, capabilities=caps,
    )


@router.post("/users/{user_id}/assign", status_code=status.HTTP_201_CREATED)
async def assign_capability(
    user_id: str, data: UserCapabilityAssign,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cap_def = db.query(CapabilityDefinition).filter(CapabilityDefinition.code == data.capability_code).first()
    if not cap_def:
        raise HTTPException(status_code=404, detail=f"Capability '{data.capability_code}' not found")
    existing = db.query(UserCapability).filter(
        UserCapability.user_id == user_id,
        UserCapability.capability_id == cap_def.id,
        UserCapability.tenant_id == current_user["tenant_id"],
    ).first()
    if existing:
        existing.granted = data.granted
        existing.granted_by = current_user["email"]
    else:
        db.add(UserCapability(
            user_id=user_id, capability_id=cap_def.id,
            granted=data.granted, granted_by=current_user["email"],
            tenant_id=current_user["tenant_id"],
        ))
    db.commit()
    return {"status": "ok", "capability": data.capability_code, "granted": data.granted}


@router.post("/check")
async def check_capability(
    capability_code: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["user_id"]
    cap_def = db.query(CapabilityDefinition).filter(CapabilityDefinition.code == capability_code).first()
    if not cap_def:
        return {"capability": capability_code, "granted": False, "agent_mode": "standard", "trust_score": 0.0}
    granted, _ = _resolve_capability(db, user_id, cap_def, current_user["tenant_id"])
    trust_score = _get_user_trust(db, user_id)
    return {
        "capability": capability_code, "granted": granted,
        "agent_mode": "standard", "trust_score": trust_score,
    }
