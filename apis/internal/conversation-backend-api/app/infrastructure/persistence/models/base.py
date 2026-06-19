"""Base model re-exports from shared."""

from shared.database import Base, TenantMixin, generate_uuid, utc_now

__all__ = ["Base", "TenantMixin", "generate_uuid", "utc_now"]
