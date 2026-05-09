"""Shared settings configuration with support for API-prefixed variables."""

import os
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    """Base settings with environment variable support.

    Each microservice inherits from this and adds its own fields.
    API-specific overrides via env prefix: {API_NAME}_API_{SETTING}
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = "development"
    debug: bool = False

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or console

    # Database
    database_url: Optional[str] = None

    # JWT
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # API Configuration
    api_port: int = 8000
    api_host: str = "0.0.0.0"

    # CORS
    cors_origins: List[str] = ["http://localhost:4200"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    cors_allow_headers: List[str] = ["Content-Type", "Authorization"]

    # Observability
    otel_exporter_otlp_endpoint: Optional[str] = None

    # Membrane Integration Platform
    membrane_workspace_key: Optional[str] = None
    membrane_workspace_secret: Optional[str] = None
    membrane_client_token: Optional[str] = None
    membrane_api_url: str = "https://api.getmembrane.com"
    # HMAC-SHA256 secret used to verify incoming Membrane webhooks.
    # Configure the same value in Membrane Console → Admin → Webhooks → Secret.
    membrane_webhook_secret: Optional[str] = None

    # Auth-specific (used by auth-api seeding, ignored by other services)
    admin_email: str = "admin@croo.digital"
    admin_password: Optional[str] = None
    admin_first_name: str = "Admin"
    admin_last_name: str = "Croo"
    secret_key: Optional[str] = None
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    rate_limit_max_attempts: int = 5
    rate_limit_window_minutes: int = 15

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Enforce strict security constraints in non-development environments."""
        # Fallback: if JWT_SECRET_KEY is empty but SECRET_KEY is set, use it.
        # Many deployments use a single SECRET_KEY env var.
        if not self.jwt_secret_key and self.secret_key:
            self.jwt_secret_key = self.secret_key

        is_dev = self.environment.lower() in ("development", "dev")

        if not is_dev:
            if not self.jwt_secret_key or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be set and at least 32 characters "
                    f"in '{self.environment}' environment"
                )
            if self.debug:
                raise ValueError(f"DEBUG must be False in '{self.environment}'")
            if "*" in self.cors_origins:
                raise ValueError(f"CORS wildcard '*' forbidden in '{self.environment}'")
        else:
            if not self.jwt_secret_key:
                self.jwt_secret_key = "dev-only-secret-not-for-production"

        return self


@lru_cache()
def get_settings(api_name: Optional[str] = None) -> Settings:
    """Get settings with optional API-specific overrides.

    Usage:
        settings = get_settings("auth")        # loads AUTH_API_* vars
        settings = get_settings("crm-backend") # loads CRM_BACKEND_API_* vars
    """
    base_settings = Settings()

    if api_name:
        api_prefix = f"{api_name.upper().replace('-', '_')}_API_"
        api_settings_dict = {}
        for key, value in os.environ.items():
            if key.startswith(api_prefix):
                setting_key = key[len(api_prefix):].lower()
                api_settings_dict[setting_key] = value
        if api_settings_dict:
            base_settings = Settings(**{**base_settings.model_dump(), **api_settings_dict})

    return base_settings
