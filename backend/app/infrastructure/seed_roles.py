"""Seed default roles and permissions for RBAC."""

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.role import Role, Permission, RolePermission, UserRole
from app.domain.entities.user import User
from app.infrastructure.persistence.role_repository import RoleRepository

logger = structlog.get_logger(__name__)

# All system permissions
PERMISSIONS = [
    # Organization
    ("organization", "read", "View organizations"),
    ("organization", "write", "Create/update organizations"),
    ("organization", "delete", "Delete organizations"),
    # Contact
    ("contact", "read", "View contacts"),
    ("contact", "write", "Create/update contacts"),
    ("contact", "delete", "Delete contacts"),
    # Opportunity
    ("opportunity", "read", "View opportunities"),
    ("opportunity", "write", "Create/update opportunities"),
    ("opportunity", "delete", "Delete opportunities"),
    # Quote
    ("quote", "read", "View quotes"),
    ("quote", "write", "Create/update quotes"),
    ("quote", "delete", "Delete quotes"),
    # Activity
    ("activity", "read", "View activities"),
    ("activity", "write", "Create/update activities"),
    ("activity", "delete", "Delete activities"),
    # Workflow
    ("workflow", "read", "View workflows"),
    ("workflow", "write", "Create/update workflows"),
    ("workflow", "delete", "Delete workflows"),
    ("workflow", "execute", "Execute workflows"),
    # Bob
    ("bob", "chat", "Use Bob chat"),
    ("bob", "voice", "Use Bob voice"),
    ("bob", "configure", "Configure Bob settings"),
    # BCC
    ("bcc", "read", "View Bob Control Center"),
    ("bcc", "write", "Manage Bob Control Center"),
    # Knowledge Base
    ("kb", "read", "View knowledge base"),
    ("kb", "write", "Manage knowledge base"),
    # Settings
    ("settings", "read", "View settings"),
    ("settings", "write", "Manage settings"),
    # User Management
    ("user", "read", "View users"),
    ("user", "write", "Update users"),
    ("user", "manage", "Manage user roles"),
    # Role Management
    ("role", "read", "View roles"),
    ("role", "write", "Manage roles"),
    # Training
    ("training", "read", "View training"),
    ("training", "write", "Manage training"),
]

# Default role definitions
ROLE_DEFINITIONS = {
    "admin": {
        "description": "Full access to all features",
        "permissions": "*",  # all permissions
    },
    "manager": {
        "description": "Full access except role and settings management",
        "permissions": [
            "organization:*", "contact:*", "opportunity:*", "quote:*",
            "activity:*", "workflow:*", "bob:*", "bcc:*", "kb:*",
            "settings:read", "user:read", "user:write",
            "role:read", "training:*",
        ],
    },
    "member": {
        "description": "Standard user — read/write access to business entities",
        "permissions": [
            "organization:read", "organization:write",
            "contact:read", "contact:write",
            "opportunity:read", "opportunity:write",
            "quote:read", "quote:write",
            "activity:read", "activity:write",
            "workflow:read", "workflow:execute",
            "bob:chat", "bob:voice",
            "bcc:read", "kb:read",
            "settings:read", "user:read",
            "role:read", "training:read",
        ],
    },
    "readonly": {
        "description": "Read-only access to all business entities",
        "permissions": [
            "organization:read", "contact:read", "opportunity:read",
            "quote:read", "activity:read", "workflow:read",
            "bob:chat", "bcc:read", "kb:read",
            "settings:read", "user:read", "role:read", "training:read",
        ],
    },
}


def _match_permission(perm_key: str, patterns: list[str]) -> bool:
    """Check if a permission key matches any of the patterns (supports wildcard)."""
    resource, action = perm_key.split(":")
    for pattern in patterns:
        if pattern == perm_key:
            return True
        p_resource, p_action = pattern.split(":")
        if p_resource == resource and p_action == "*":
            return True
    return False


def seed_roles(db: Session, tenant_id: str) -> None:
    """Seed default roles and permissions for a tenant."""
    repo = RoleRepository(db)

    # 1. Seed all permissions (global, not tenant-scoped)
    all_perms: dict[str, Permission] = {}
    for resource, action, description in PERMISSIONS:
        perm = repo.get_or_create_permission(resource, action, description)
        all_perms[perm.key] = perm
    db.commit()
    logger.info("permissions_seeded", count=len(all_perms))

    # 2. Seed roles for tenant
    for role_name, role_def in ROLE_DEFINITIONS.items():
        existing = repo.get_role_by_name(role_name, tenant_id)
        if existing:
            continue

        role = Role(
            name=role_name,
            description=role_def["description"],
            tenant_id=tenant_id,
            is_system=True,
        )
        db.add(role)
        db.flush()

        # Assign permissions
        if role_def["permissions"] == "*":
            # Admin gets ALL
            for perm in all_perms.values():
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        else:
            for perm_key, perm in all_perms.items():
                if _match_permission(perm_key, role_def["permissions"]):
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    db.commit()
    logger.info("roles_seeded", tenant_id=tenant_id)

    # 3. Assign admin role to admin user if not yet assigned
    admin_role = repo.get_role_by_name("admin", tenant_id)
    if admin_role:
        admin_users = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.role == "admin",
        ).all()
        for user in admin_users:
            existing = db.query(UserRole).filter(
                UserRole.user_id == user.id,
                UserRole.role_id == admin_role.id,
            ).first()
            if not existing:
                db.add(UserRole(user_id=user.id, role_id=admin_role.id))
                logger.info("admin_role_assigned", user_id=user.id)
        db.commit()
