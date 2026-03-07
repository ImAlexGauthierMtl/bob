"""Application configuration via Pydantic settings."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    environment: str = "development"
    debug: bool = True
    api_port: int = 8000

    # Database
    database_url: str = "postgresql://croo:croo@localhost:5432/croo_digital_experience"

    # JWT
    secret_key: str = "CHANGE-ME-IN-PRODUCTION-USE-LONG-RANDOM-STRING"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: List[str] = ["http://localhost:4200", "http://localhost:4201"]

    # Rate limiting
    rate_limit_max_attempts: int = 5
    rate_limit_window_minutes: int = 15

    # Groq (LLM)
    groq_api_key: str = ""
    groq_default_model: str = "llama-3.3-70b-versatile"

    # Bob Agent
    bob_model: str = "qwen/qwen3-32b"
    bob_temperature: float = 0.3
    bob_max_history: int = 20
    bob_session_ttl_minutes: int = 60

    # Voice (Phase 2 — Pipecat)
    groq_whisper_model: str = "whisper-large-v3-turbo"
    groq_tts_model: str = "canopylabs/orpheus-v1-english"
    groq_tts_voice: str = "autumn"
    voice_vad_threshold: float = 0.5
    voice_max_session_minutes: int = 30

    # Serper.dev (Search)
    serper_api_key: str = ""

    # Admin seed
    admin_email: str = "admin@croo.digital"
    admin_password: str = "Admin123!"
    admin_first_name: str = "Admin"
    admin_last_name: str = "Croo"

    # Webhooks
    webhook_api_key: str = "croo-webhook-dev-key"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
