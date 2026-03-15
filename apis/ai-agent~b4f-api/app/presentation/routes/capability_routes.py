"""Capability routes — view and manage user capabilities.

Cross-service note: User entity lives in Auth API, but we share the same DB.
We query the 'users' table directly via text SQL for cross-service lookups.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.application.services.capability_resolver import CapabilityResolver
from app.domain.entities.capability import CapabilityDefinition, UserCapability
from app.presentation.schemas.capability_schemas import (
    CapabilityDefinitionResponse,
    UserCapabilityAssign,
    UserCapabilityResponse,
    UserCapabilitiesResponse,
)

router = APIRouter(prefix="/api/v1/capabilities")


def _get_user_trust(db: Session, user_id: str) -> float:
    """Cross-service query to get user trust_score from Auth API's users table."""
    result = db.execute(text("SELECT trust_score FROM users WHERE id = :uid"), {"uid": user_id}).first()
    return result[0] if result else 0.0


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
    resolver = CapabilityResolver(db)
    caps = resolver.get_all_capabilities(user_id, current_user["tenant_id"])
    trust_score = _get_user_trust(db, user_id)
    return UserCapabilitiesResponse(
        user_id=user_id, agent_mode="standard",
        trust_score=trust_score,
        capabilities=[UserCapabilityResponse(**c) for c in caps],
    )


@router.get("/me", response_model=UserCapabilitiesResponse)
async def get_my_capabilities(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["user_id"]
    resolver = CapabilityResolver(db)
    caps = resolver.get_all_capabilities(user_id, current_user["tenant_id"])
    trust_score = _get_user_trust(db, user_id)
    return UserCapabilitiesResponse(
        user_id=user_id, agent_mode="standard",
        trust_score=trust_score,
        capabilities=[UserCapabilityResponse(**c) for c in caps],
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
    resolver = CapabilityResolver(db)
    granted = resolver.can(user_id, capability_code, current_user["tenant_id"])
    trust_score = _get_user_trust(db, user_id)
    return {
        "capability": capability_code, "granted": granted,
        "agent_mode": "standard", "trust_score": trust_score,
    }
