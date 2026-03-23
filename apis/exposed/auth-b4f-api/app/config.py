"""Auth API configuration — extends shared settings."""

from shared.config import Settings
from typing import Optional


class AuthSettings(Settings):
    """Auth-specific settings."""

    # Admin seed
    admin_email: str = "admin@croo.digital"
    admin_password: str = ""
    admin_first_name: str = "Admin"
    admin_last_name: str = "Croo"

    # Token lifetimes
    access_token_expire_minutes: int = 1440  # 24 hours
    refresh_token_expire_days: int = 7

    # Rate limiting
    rate_limit_max_attempts: int = 5
    rate_limit_window_minutes: int = 15

    # Secret key (alias for jwt_secret_key)
    secret_key: str = ""


settings = AuthSettings()
