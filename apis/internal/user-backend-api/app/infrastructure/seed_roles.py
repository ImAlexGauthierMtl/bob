"""Seed default roles and permissions for RBAC."""

from shared.infrastructure import get_logger
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.role import Role, Permission, RolePermission, UserRole
from app.infrastructure.persistence.models.user import User
from app.infrastructure.persistence.role_repository import RoleRepository

logger = get_logger(__name__)

PERMISSIONS = [
    ("organization", "read", "View organizations"),
    ("organization", "write", "Create/update organizations"),
    ("organization", "delete", "Delete organizations"),
    ("contact", "read", "View contacts"),
    ("contact", "write", "Create/update contacts"),
    ("contact", "delete", "Delete contacts"),
    ("opportunity", "read", "View opportunities"),
    ("opportunity", "write", "Create/update opportunities"),
    ("opportunity", "delete", "Delete opportunities"),
    ("quote", "read", "View quotes"),
    ("quote", "write", "Create/update quotes"),
    ("quote", "delete", "Delete quotes"),
    ("activity", "read", "View activities"),
    ("activity", "write", "Create/update activities"),
    ("activity", "delete", "Delete activities"),
    ("workflow", "read", "View workflows"),
    ("workflow", "write", "Create/update workflows"),
    ("workflow", "delete", "Delete workflows"),
    ("workflow", "execute", "Execute workflows"),
    ("bob", "chat", "Use Bob chat"),
    ("bob", "voice", "Use Bob voice"),
    ("bob", "configure", "Configure Bob settings"),
    ("bcc", "read", "View Bob Control Center"),
    ("bcc", "write", "Manage Bob Control Center"),
    ("kb", "read", "View knowledge base"),
    ("kb", "write", "Manage knowledge base"),
    ("settings", "read", "View settings"),
    ("settings", "write", "Manage settings"),
    ("user", "read", "View users"),
    ("user", "write", "Update users"),
    ("user", "manage", "Manage user roles"),
    ("role", "read", "View roles"),
    ("role", "write", "Manage roles"),
    ("training", "read", "View training"),
    ("training", "write", "Manage training"),
]

ROLE_DEFINITIONS = {
    "admin": {"description": "Full access to all features", "permissions": "*"},
    "manager": {
        "description": "Full access except role and settings management",
        "permissions": [
            "organization:*", "contact:*", "opportunity:*", "quote:*",
            "activity:*", "workflow:*", "bob:*", "bcc:*", "kb:*",
            "settings:read", "user:read", "user:write", "role:read", "training:*",
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
            "settings:read", "user:read", "role:read", "training:read",
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

    all_perms: dict[str, Permission] = {}
    for resource, action, description in PERMISSIONS:
        perm = repo.get_or_create_permission(resource, action, description)
        all_perms[perm.key] = perm
    db.commit()
    logger.info("permissions_seeded", count=len(all_perms))

    for role_name, role_def in ROLE_DEFINITIONS.items():
        existing = repo.get_role_by_name(role_name, tenant_id)
        if existing:
            continue
        role = Role(
            name=role_name, description=role_def["description"],
            tenant_id=tenant_id, is_system=True,
        )
        db.add(role)
        db.flush()
        if role_def["permissions"] == "*":
            for perm in all_perms.values():
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        else:
            for perm_key, perm in all_perms.items():
                if _match_permission(perm_key, role_def["permissions"]):
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()
    logger.info("roles_seeded", tenant_id=tenant_id)

    admin_role = repo.get_role_by_name("admin", tenant_id)
    if admin_role:
        admin_users = db.query(User).filter(
            User.tenant_id == tenant_id, User.role == "admin",
        ).all()
        for user in admin_users:
            existing = db.query(UserRole).filter(
                UserRole.user_id == user.id, UserRole.role_id == admin_role.id,
            ).first()
            if not existing:
                db.add(UserRole(user_id=user.id, role_id=admin_role.id))
                logger.info("admin_role_assigned", user_id=user.id)
        db.commit()



def backfill_user_roles(db: Session, tenant_id: str) -> None:
    """Assign UserRole entries to existing users who are missing them.

    This is needed because the original user-creation code only set the
    User.role string column but never inserted a UserRole row. Non-admin
    users ended up with empty roles/permissions after login, causing
    permission-denied errors that appeared as connection problems on the
    frontend.
    """
    repo = RoleRepository(db)
    users = db.query(User).filter(User.tenant_id == tenant_id).all()
    assigned = 0
    for user in users:
        role_name = user.role or "member"
        matching_role = repo.get_role_by_name(role_name, tenant_id)
        if not matching_role:
            logger.warning("backfill_skip_no_role", user_id=user.id, role_name=role_name)
            continue
        existing = db.query(UserRole).filter(
            UserRole.user_id == user.id, UserRole.role_id == matching_role.id,
        ).first()
        if not existing:
            db.add(UserRole(user_id=user.id, role_id=matching_role.id))
            assigned += 1
    if assigned:
        db.commit()
        logger.info("backfill_user_roles", tenant_id=tenant_id, assigned=assigned)
