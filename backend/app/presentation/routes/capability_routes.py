"""Capability routes — view and manage user capabilities."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.application.services.capability_resolver import CapabilityResolver
from app.domain.entities.capability import CapabilityDefinition, UserCapability
from app.domain.entities.user import User
from app.infrastructure.persistence.user_repository import UserRepository
from app.presentation.schemas.capability_schemas import (
    CapabilityDefinitionResponse,
    UserCapabilityAssign,
    UserCapabilityResponse,
    UserCapabilitiesResponse,
)

router = APIRouter(prefix="/api/v1/capabilities")


@router.get("/catalog", response_model=list[CapabilityDefinitionResponse])
async def list_capability_catalog(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all available capability definitions."""
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
    """Get all resolved capabilities for a user."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    resolver = CapabilityResolver(db)
    caps = resolver.get_all_capabilities(user_id, current_user["tenant_id"])
    agent_mode = resolver.get_agent_mode(user)

    return UserCapabilitiesResponse(
        user_id=user_id,
        agent_mode=agent_mode,
        trust_score=user.trust_score,
        capabilities=[UserCapabilityResponse(**c) for c in caps],
    )


@router.get("/me", response_model=UserCapabilitiesResponse)
async def get_my_capabilities(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get resolved capabilities for the current user."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    resolver = CapabilityResolver(db)
    caps = resolver.get_all_capabilities(user.id, current_user["tenant_id"])
    agent_mode = resolver.get_agent_mode(user)

    return UserCapabilitiesResponse(
        user_id=user.id,
        agent_mode=agent_mode,
        trust_score=user.trust_score,
        capabilities=[UserCapabilityResponse(**c) for c in caps],
    )


@router.post("/users/{user_id}/assign", status_code=status.HTTP_201_CREATED)
async def assign_capability(
    user_id: str,
    data: UserCapabilityAssign,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assign or revoke a capability for a user."""
    cap_def = db.query(CapabilityDefinition).filter(
        CapabilityDefinition.code == data.capability_code,
    ).first()
    if not cap_def:
        raise HTTPException(status_code=404, detail=f"Capability '{data.capability_code}' not found")

    # Upsert
    existing = db.query(UserCapability).filter(
        UserCapability.user_id == user_id,
        UserCapability.capability_id == cap_def.id,
        UserCapability.tenant_id == current_user["tenant_id"],
    ).first()

    if existing:
        existing.granted = data.granted
        existing.granted_by = current_user["email"]
    else:
        uc = UserCapability(
            user_id=user_id,
            capability_id=cap_def.id,
            granted=data.granted,
            granted_by=current_user["email"],
            tenant_id=current_user["tenant_id"],
        )
        db.add(uc)

    db.commit()
    return {"status": "ok", "capability": data.capability_code, "granted": data.granted}


@router.post("/check")
async def check_capability(
    capability_code: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if the current user has a specific capability."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    resolver = CapabilityResolver(db)
    granted = resolver.can(user.id, capability_code, current_user["tenant_id"])
    agent_mode = resolver.get_agent_mode(user)

    return {
        "capability": capability_code,
        "granted": granted,
        "agent_mode": agent_mode,
        "trust_score": user.trust_score,
    }
