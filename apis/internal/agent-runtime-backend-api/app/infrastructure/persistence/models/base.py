"""Base model re-exports from shared."""

from shared.database import Base, generate_uuid, utc_now

__all__ = ["Base", "generate_uuid", "utc_now"]
