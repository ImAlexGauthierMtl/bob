"""Base model with tenant_id and audit fields — reexports from shared."""

from shared.database import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid, utc_now

__all__ = ["Base", "TenantMixin", "AuditMixin", "SoftDeleteMixin", "generate_uuid", "utc_now"]
