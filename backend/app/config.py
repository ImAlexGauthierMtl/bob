"""Application configuration via Pydantic settings."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    environment: str = "development"
    debug: bool = True
    api_port: int = 4500

    # Database
    database_url: str = "postgresql://croo:croo@localhost:5432/croo_digital_experience"

    # JWT
    secret_key: str = ""  # MUST be set via .env — use: openssl rand -hex 64
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: List[str] = ["http://localhost:4200", "http://localhost:4201", "http://localhost:4700"]

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

    # DashScope / Alibaba Cloud (Qwen3-TTS for multilingual voice)
    dashscope_api_key: str = ""
    dashscope_tts_model: str = "qwen3-tts-flash"
    # instruct-flash supports instructions (tone/emotion) but only for CN/EN
    # Using it for non-CN/EN languages causes accent bleed (Chinese accent)
    dashscope_tts_instruct_model: str = "qwen3-tts-instruct-flash"
    dashscope_tts_voice: str = "Cherry"
    # Rick — custom cloned voice (zero-shot via ref_audio)
    # Point to a WAV file (mono, 24kHz): set RICK_REF_AUDIO_PATH=/path/to/rick_ref.wav
    rick_ref_audio_path: str = ""

    # Anthropic (Deep Agent — Opus 4.6)
    anthropic_api_key: str = ""

    # OpenRouter (Deep Agent — Claude Opus 4.6 via OpenRouter)
    openrouter_api_key: str = ""

    # Redis (session store)
    redis_url: str = ""

    # Serper.dev (Search)
    serper_api_key: str = ""

    # Hunter.io (Domain Search & Enrichment)
    hunter_api_key: str = ""

    # Admin seed
    admin_email: str = "admin@croo.digital"
    admin_password: str = ""  # MUST be set via .env
    admin_first_name: str = "Admin"
    admin_last_name: str = "Croo"

    # Microsoft 365 (MS Graph API)
    ms365_client_id: str = ""  # Azure AD App Client ID
    ms365_client_secret: str = ""  # Azure AD App Client Secret
    ms365_tenant_id: str = "common"  # Azure AD Tenant ID — "common" for multi-tenant
    ms365_redirect_uri: str = "http://localhost:4500/api/v1/ms365/callback"
    ms365_sync_interval_seconds: int = 120  # Polling fallback interval
    ms365_webhook_host: str = ""  # Public HTTPS host for webhook notifications

    # Webhooks
    webhook_api_key: str = ""  # MUST be set via .env

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
