"""Runtime provider factory."""

from __future__ import annotations

import os

from app.application.ports import RuntimeProviderPort
from app.infrastructure.providers.fireworks_provider import FireworksRuntimeProvider
from app.infrastructure.providers.local_provider import LocalRuntimeProvider


def create_runtime_provider() -> RuntimeProviderPort:
    provider_name = os.getenv("AGENT_RUNTIME_PROVIDER", "auto").strip().lower()
    if provider_name in {"local", "mock", "local_mock"}:
        return LocalRuntimeProvider()

    api_key = os.getenv("FIREWORKS_API_KEY", "").strip()
    if provider_name in {"auto", "fireworks"} and api_key:
        return FireworksRuntimeProvider(
            api_key=api_key,
            base_url=os.getenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"),
            model=os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/kimi-k2p7-code"),
            temperature=float(os.getenv("FIREWORKS_TEMPERATURE", "0.1")),
            top_p=float(os.getenv("FIREWORKS_TOP_P", "0.8")),
            timeout_seconds=float(os.getenv("FIREWORKS_TIMEOUT_SECONDS", "60")),
        )

    if provider_name == "fireworks":
        raise RuntimeError("fireworks_provider_missing_api_key")

    return LocalRuntimeProvider()
