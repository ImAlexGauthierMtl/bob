"""Capability data access."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.capability import CapabilityDefinition, DeptCapability, UserCapability
from app.infrastructure.persistence.models.department import UserDepartment


class CapabilityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_catalog(self) -> list[CapabilityDefinition]:
        return self.db.query(CapabilityDefinition).order_by(
            CapabilityDefinition.scope,
            CapabilityDefinition.code,
        ).all()

    def get_user_trust(self, user_id: str) -> float:
        result = self.db.execute(text("SELECT trust_score FROM users WHERE id = :uid"), {"uid": user_id}).first()
        return result[0] if result else 0.0

    def resolve_capability(
        self,
        user_id: str,
        cap_def: CapabilityDefinition,
        tenant_id: str,
    ) -> tuple[bool, str]:
        user_override = self.db.query(UserCapability).filter(
            UserCapability.user_id == user_id,
            UserCapability.capability_id == cap_def.id,
            UserCapability.tenant_id == tenant_id,
        ).first()
        if user_override:
            return user_override.granted, "user"

        user_dept_ids = [
            user_department.department_id
            for user_department in self.db.query(UserDepartment).filter(UserDepartment.user_id == user_id).all()
        ]
        if user_dept_ids:
            dept_caps = self.db.query(DeptCapability).filter(
                DeptCapability.department_id.in_(user_dept_ids),
                DeptCapability.capability_id == cap_def.id,
                DeptCapability.tenant_id == tenant_id,
            ).all()
            if dept_caps:
                return any(dept_cap.granted for dept_cap in dept_caps), "department"

        return cap_def.default_enabled, "system"

    def get_user_capabilities(self, user_id: str, tenant_id: str) -> dict:
        capabilities = []
        for cap_def in self.list_catalog():
            granted, source = self.resolve_capability(user_id, cap_def, tenant_id)
            capabilities.append({
                "code": cap_def.code,
                "name": cap_def.name,
                "scope": cap_def.scope,
                "module": cap_def.module,
                "risk_level": cap_def.risk_level,
                "granted": granted,
                "source": source,
            })

        return {
            "user_id": user_id,
            "agent_mode": "standard",
            "trust_score": self.get_user_trust(user_id),
            "capabilities": capabilities,
        }

    def assign_capability(
        self,
        user_id: str,
        capability_code: str,
        granted: bool,
        tenant_id: str,
        granted_by: str,
    ) -> dict | None:
        cap_def = self.db.query(CapabilityDefinition).filter(
            CapabilityDefinition.code == capability_code,
        ).first()
        if not cap_def:
            return None

        existing = self.db.query(UserCapability).filter(
            UserCapability.user_id == user_id,
            UserCapability.capability_id == cap_def.id,
            UserCapability.tenant_id == tenant_id,
        ).first()
        if existing:
            existing.granted = granted
            existing.granted_by = granted_by
        else:
            self.db.add(UserCapability(
                user_id=user_id,
                capability_id=cap_def.id,
                granted=granted,
                granted_by=granted_by,
                tenant_id=tenant_id,
            ))
        self.db.commit()
        return {"status": "ok", "capability": capability_code, "granted": granted}

    def check_capability(self, user_id: str, capability_code: str, tenant_id: str) -> dict:
        cap_def = self.db.query(CapabilityDefinition).filter(CapabilityDefinition.code == capability_code).first()
        if not cap_def:
            return {
                "capability": capability_code,
                "granted": False,
                "agent_mode": "standard",
                "trust_score": 0.0,
            }

        granted, _ = self.resolve_capability(user_id, cap_def, tenant_id)
        return {
            "capability": capability_code,
            "granted": granted,
            "agent_mode": "standard",
            "trust_score": self.get_user_trust(user_id),
        }
