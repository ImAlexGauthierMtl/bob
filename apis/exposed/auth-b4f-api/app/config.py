"""Auth API configuration — extends shared settings."""

from shared.config import Settings
from pydantic import model_validator


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

    @model_validator(mode="after")
    def sync_secret_keys(self) -> "AuthSettings":
        """Ensure jwt_secret_key and secret_key are always in sync.

        Prevents token signing/verification mismatch when only one
        of SECRET_KEY or JWT_SECRET_KEY is set in the environment.
        """
        if self.secret_key and not self.jwt_secret_key:
            self.jwt_secret_key = self.secret_key
        elif self.jwt_secret_key and not self.secret_key:
            self.secret_key = self.jwt_secret_key
        return self


settings = AuthSettings()
