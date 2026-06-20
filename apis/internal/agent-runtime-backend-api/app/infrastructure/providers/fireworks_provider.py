"""Fireworks OpenAI-compatible runtime provider."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.application.ports import RuntimeProviderPort
from app.domain import RuntimeModelResult, RuntimeToolCall


class FireworksRuntimeProvider(RuntimeProviderPort):
    supports_tool_choice = True

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
        top_p: float,
        timeout_seconds: float,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.timeout_seconds = timeout_seconds

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        trace_id: str,
    ) -> RuntimeModelResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Trace-Id": trace_id,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        choice = data.get("choices", [{}])[0]
        message = choice.get("message") or {}
        tool_calls = [
            _to_tool_call(index=index, raw_tool_call=raw_tool_call)
            for index, raw_tool_call in enumerate(message.get("tool_calls") or [])
        ]
        return RuntimeModelResult(
            content=message.get("content") or "",
            provider="fireworks",
            model=self.model,
            mode="provider_fireworks",
            tool_calls=tool_calls,
            raw_metadata={
                "finish_reason": choice.get("finish_reason"),
                "usage": data.get("usage") or {},
            },
        )


def _to_tool_call(*, index: int, raw_tool_call: dict[str, Any]) -> RuntimeToolCall:
    function = raw_tool_call.get("function") or {}
    raw_arguments = function.get("arguments") or "{}"
    try:
        arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
    except json.JSONDecodeError:
        arguments = {"raw": raw_arguments}
    return RuntimeToolCall(
        id=raw_tool_call.get("id") or f"tool_call_{index}",
        name=function.get("name") or raw_tool_call.get("name") or "unknown_tool",
        arguments=arguments if isinstance(arguments, dict) else {"value": arguments},
    )
