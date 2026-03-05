# Template: Configuration Applicative (pydantic-settings)

> Recette pour créer la configuration centralisée avec variables d'environnement.
> **Zéro décision** : suivre exactement ce pattern.

## Fichier à créer

`shared/config/settings.py`

## Code exact

```python
"""Shared settings configuration with support for API-prefixed variables."""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    """Base settings with environment variable support."""

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
    cors_origins: list[str] = ["http://localhost:4200"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    cors_allow_headers: list[str] = ["Content-Type", "Authorization"]

    # Observability
    otel_exporter_otlp_endpoint: Optional[str] = None

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Enforce strict security constraints in non-development environments."""
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
    """Get settings with optional API-specific overrides."""
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
```

## Règles NON-NÉGOCIABLES

1. `pydantic-settings` avec `BaseSettings` — jamais `os.getenv()` direct
2. Validation en production : JWT key ≥ 32 chars, debug=False, pas de CORS wildcard
3. Défauts sûrs pour dev, strict pour prod
4. `@lru_cache()` sur `get_settings()` pour singleton
5. Support des overrides par API avec préfixe `{API_NAME}_API_`
6. Fichier `.env` chargé automatiquement
