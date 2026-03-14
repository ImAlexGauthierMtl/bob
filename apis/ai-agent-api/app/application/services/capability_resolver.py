"""Capability resolver — cascade permission resolution.

Resolution order: system > company > department > user

1. System capabilities (from CapabilityDefinition.default_enabled) — always active
2. Company overrides — admin can disable/enable at tenant level (future)
3. Department defaults — from DeptCapability for user's departments
4. User overrides — from UserCapability (highest priority)

The trust_score gates which agent execution modes are available:
- 0.0-0.3: suggest only
- 0.3-0.6: suggest + approval
- 0.6-1.0: suggest + approval + auto
"""

from typing import List, Optional

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.capability import CapabilityDefinition, UserCapability, DeptCapability
from app.domain.entities.department import UserDepartment


logger = structlog.get_logger(__name__)


class CapabilityResolver:
    """Resolves capabilities for a user using cascade logic."""

    def __init__(self, db: Session):
        self.db = db

    def can(self, user_id: str, capability_code: str, tenant_id: str) -> bool:
        """Check if a user has a specific capability.

        Resolution cascade:
        1. Check UserCapability override (highest priority)
        2. Check DeptCapability for all user's departments
        3. Fall back to CapabilityDefinition.default_enabled
        """
        # Get the capability definition
        cap_def = self.db.query(CapabilityDefinition).filter(
            CapabilityDefinition.code == capability_code,
        ).first()

        if not cap_def:
            logger.warning("capability_not_found", code=capability_code)
            return False

        # 1. User-level override (highest priority)
        user_override = self.db.query(UserCapability).filter(
            UserCapability.user_id == user_id,
            UserCapability.capability_id == cap_def.id,
            UserCapability.tenant_id == tenant_id,
        ).first()

        if user_override:
            return user_override.granted

        # 2. Department-level — check all user's departments
        user_dept_ids = [
            ud.department_id for ud in
            self.db.query(UserDepartment).filter(
                UserDepartment.user_id == user_id,
            ).all()
        ]

        if user_dept_ids:
            dept_caps = self.db.query(DeptCapability).filter(
                DeptCapability.department_id.in_(user_dept_ids),
                DeptCapability.capability_id == cap_def.id,
                DeptCapability.tenant_id == tenant_id,
            ).all()

            # If any department grants it, it's granted
            # (unless explicitly revoked at user level — already checked)
            if dept_caps:
                return any(dc.granted for dc in dept_caps)

        # 3. Fall back to system default
        return cap_def.default_enabled

    def get_all_capabilities(self, user_id: str, tenant_id: str) -> List[dict]:
        """Get all capabilities with their resolved status for a user."""
        all_defs = self.db.query(CapabilityDefinition).order_by(
            CapabilityDefinition.scope,
            CapabilityDefinition.code,
        ).all()

        result = []
        for cap_def in all_defs:
            granted = self.can(user_id, cap_def.code, tenant_id)
            result.append({
                "code": cap_def.code,
                "name": cap_def.name,
                "scope": cap_def.scope,
                "module": cap_def.module,
                "risk_level": cap_def.risk_level,
                "granted": granted,
                "source": self._get_source(user_id, cap_def.id, tenant_id),
            })

        return result

    def get_agent_mode(self, user: User) -> str:
        """Determine Bob's execution mode based on trust_score.

        Returns: 'suggest' | 'approval' | 'auto'
        """
        score = user.trust_score or 0.0
        if score >= 0.6:
            return "auto"
        elif score >= 0.3:
            return "approval"
        return "suggest"

    def _get_source(self, user_id: str, cap_id: str, tenant_id: str) -> str:
        """Determine where a capability resolution came from."""
        user_override = self.db.query(UserCapability).filter(
            UserCapability.user_id == user_id,
            UserCapability.capability_id == cap_id,
            UserCapability.tenant_id == tenant_id,
        ).first()
        if user_override:
            return "user"

        user_dept_ids = [
            ud.department_id for ud in
            self.db.query(UserDepartment).filter(
                UserDepartment.user_id == user_id,
            ).all()
        ]
        if user_dept_ids:
            dept_cap = self.db.query(DeptCapability).filter(
                DeptCapability.department_id.in_(user_dept_ids),
                DeptCapability.capability_id == cap_id,
                DeptCapability.tenant_id == tenant_id,
            ).first()
            if dept_cap:
                return "department"

        return "system"
