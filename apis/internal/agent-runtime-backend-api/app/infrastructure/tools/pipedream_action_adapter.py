"""Pipedream Connect read adapter for Bob's MCP gateway."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from uuid import uuid4

from shared.event_bus import Event, event_bus

from app.domain import InternalContext


class PipedreamActionAdapterError(Exception):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail or {}


class PipedreamActionAdapter:
    """Execute safe, read-only Pipedream actions for connected user accounts."""

    request_event_type = "agent-runtime.pipedream.read.requested"

    def __init__(
        self,
        *,
        bus: Any | None = None,
        timeout_seconds: float = 45.0,
        poll_interval_seconds: float = 0.25,
    ) -> None:
        self.bus = bus or event_bus
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    @classmethod
    def from_env(cls) -> "PipedreamActionAdapter":
        return cls()

    async def execute_read(
        self,
        *,
        family: str,
        capability: str,
        query: str,
        limit: int,
        context: InternalContext,
        provider_preference: str | None = None,
    ) -> dict[str, Any]:
        capability_id = _normalize_capability(family=family, capability=capability)
        if family == "slack":
            return await self._execute_slack_read(
                capability=capability_id,
                query=query,
                limit=limit,
                context=context,
            )
        if family == "mail-calendar":
            return await self._execute_mail_calendar_read(
                capability=capability_id,
                query=query,
                limit=limit,
                context=context,
                provider_preference=provider_preference,
            )
        raise PipedreamActionAdapterError("pipedream_family_not_supported", detail={"family": family})

    async def _execute_slack_read(
        self,
        *,
        capability: str,
        query: str,
        limit: int,
        context: InternalContext,
    ) -> dict[str, Any]:
        connections = await self._list_connections(context=context)
        account = _first_account(connections, ("slack_v2", "slack"))
        if not account:
            return _not_connected(family="slack", capability=capability, apps=("slack_v2", "slack"))

        app_slug = str(account.get("app") or "slack_v2")
        action_prefix = "slack_v2" if app_slug == "slack_v2" else "slack"
        integration_key = "slack-v2" if app_slug == "slack_v2" else "slack"
        if capability == "channels-users":
            page_size = _bounded(limit, default=10, maximum=100)
            return await self._run_connected_action(
                action_key=f"{action_prefix}-list-channels",
                integration_key=integration_key,
                app_prop_name="slack",
                account=account,
                props={
                    "channelTypes": "public_channel",
                    "pageSize": page_size,
                    "numPages": 1,
                },
                context=context,
                family="slack",
                capability=capability,
                item_extractor=_slack_channels,
                item_limit=page_size,
            )

        if capability == "messages-read-search":
            channel_name = _extract_channel_name(query)
            channels = await self._run_connected_action(
                action_key=f"{action_prefix}-list-channels",
                integration_key=integration_key,
                app_prop_name="slack",
                account=account,
                props={"channelTypes": "public_channel", "pageSize": 100, "numPages": 1},
                context=context,
                family="slack",
                capability="channels-users",
                item_extractor=_slack_channels,
                item_limit=100,
            )
            if not channel_name:
                return {
                    **channels,
                    "status": "channel_required",
                    "capability": capability,
                    "message": "A Slack channel is required to read messages.",
                }
            channel = _find_channel(channels.get("items"), channel_name)
            if not channel:
                return {
                    **channels,
                    "status": "channel_not_found",
                    "capability": capability,
                    "requested_channel": channel_name,
                }
            return await self._run_connected_action(
                action_key=f"{action_prefix}-get-channel-history",
                integration_key=integration_key,
                app_prop_name="slack",
                account=account,
                item_limit=_bounded(limit, default=10, maximum=50),
                props={
                    "channel": channel["id"],
                    "limit": _bounded(limit, default=10, maximum=50),
                },
                context=context,
                family="slack",
                capability=capability,
                item_extractor=_slack_messages,
                extra={"channel": channel},
            )

        raise PipedreamActionAdapterError(
            "pipedream_slack_capability_not_supported",
            detail={"capability": capability},
        )

    async def _execute_mail_calendar_read(
        self,
        *,
        capability: str,
        query: str,
        limit: int,
        context: InternalContext,
        provider_preference: str | None = None,
    ) -> dict[str, Any]:
        if capability != "mail-read-search":
            raise PipedreamActionAdapterError(
                "pipedream_mail_capability_not_supported",
                detail={"capability": capability},
            )

        connections = await self._list_connections(context=context)
        provider_priority = _mail_provider_preference(query, provider_preference=provider_preference)
        account = _first_account(connections, provider_priority)
        if not account:
            return _not_connected(
                family="mail-calendar",
                capability=capability,
                apps=provider_priority,
            )

        app_slug = str(account.get("app") or "")
        if app_slug == "microsoft_outlook":
            result_limit = _bounded(limit, default=10, maximum=25)
            return await self._run_connected_action(
                action_key="microsoft_outlook-find-email",
                integration_key="microsoft-outlook",
                app_prop_name="microsoftOutlook",
                account=account,
                props={
                    "folderScope": "inbox" if _mentions_inbox(query) else "all",
                    "countOnly": False,
                },
                context=context,
                family="mail-calendar",
                capability=capability,
                item_extractor=_mail_items,
                item_limit=result_limit,
                extra={"provider_preference": provider_preference or "auto"},
            )

        gmail_props: dict[str, Any] = {}
        action_key = "gmail-find-email"
        extractor = _mail_items
        result_limit = _bounded(limit, default=10, maximum=25)
        if _mentions_labels(query):
            action_key = "gmail-list-labels"
            extractor = _gmail_labels
        else:
            gmail_props.update(
                {
                    "q": _gmail_query(query),
                    "maxResults": result_limit,
                    "format": "metadata",
                }
            )
        return await self._run_connected_action(
            action_key=action_key,
            integration_key="gmail",
            app_prop_name="gmail",
            account=account,
            props=gmail_props,
            context=context,
            family="mail-calendar",
            capability=capability,
            item_extractor=extractor,
            item_limit=result_limit,
            extra={"provider_preference": provider_preference or "auto"},
        )

    async def _run_connected_action(
        self,
        *,
        action_key: str,
        integration_key: str,
        app_prop_name: str,
        account: dict[str, Any],
        props: dict[str, Any],
        context: InternalContext,
        family: str,
        capability: str,
        item_extractor,
        item_limit: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        configured_props = {
            "integration_key": integration_key,
            "app": integration_key,
            app_prop_name: {"authProvisionId": account.get("id")},
            **props,
        }
        payload = await self._request_provider(
            context=context,
            operation="run_action",
            data={
                "action_key": action_key,
                "integration_key": integration_key,
                "input": configured_props,
            },
        )
        output = payload.get("output") if isinstance(payload, dict) else {}
        output = output if isinstance(output, dict) else {}
        error = output.get("error")
        if error:
            return {
                "status": "action_error",
                "family": family,
                "capability": capability,
                "action_key": action_key,
                "connected_account": _public_account(account),
                "external_connector_bound": True,
                "execution_mode": "pipedream_connect_action",
                "error": _compact_error(error),
            }
        items = item_extractor(output)
        if item_limit is not None:
            items = items[: max(0, item_limit)]
        result = {
            "status": "completed",
            "family": family,
            "capability": capability,
            "action_key": action_key,
            "connected_account": _public_account(account),
            "external_connector_bound": True,
            "execution_mode": "pipedream_connect_action",
            "summary": _summary(output, item_count=len(items)),
            "items": items,
        }
        if extra:
            result.update(extra)
        return result

    async def _list_connections(self, *, context: InternalContext) -> list[dict[str, Any]]:
        payload = await self._request_provider(
            context=context,
            operation="list_connections",
            data={},
        )
        items = payload.get("items") if isinstance(payload, dict) else []
        return [item for item in items if isinstance(item, dict)]

    async def _request_provider(
        self,
        *,
        context: InternalContext,
        operation: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        request_id = uuid4().hex
        response_key = f"cde:pipedream-runtime-response:{request_id}"
        await self.bus.publish(
            Event(
                event_type=self.request_event_type,
                source="agent-runtime",
                payload={
                    "request_id": request_id,
                    "response_key": response_key,
                    "operation": operation,
                    "data": data,
                    "context": {
                        "tenant_id": context.tenant_id,
                        "user_id": context.user_id,
                        "trace_id": context.trace_id,
                        "roles": list(context.roles),
                        "permissions": list(context.permissions),
                    },
                },
                trace_id=context.trace_id,
            )
        )
        envelope = await self._wait_response(response_key)
        if not envelope.get("ok"):
            raise PipedreamActionAdapterError(
                str(envelope.get("code") or "pipedream_provider_event_error"),
                detail=envelope.get("detail") if isinstance(envelope.get("detail"), dict) else {},
            )
        data = envelope.get("data")
        return data if isinstance(data, dict) else {}

    async def _wait_response(self, response_key: str) -> dict[str, Any]:
        redis = await self._response_store()
        deadline = asyncio.get_running_loop().time() + self.timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            raw = await redis.get(response_key)
            if raw:
                await redis.delete(response_key)
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                try:
                    parsed = json.loads(str(raw))
                except json.JSONDecodeError as exc:
                    raise PipedreamActionAdapterError(
                        "pipedream_event_response_invalid",
                        detail={"error": str(exc)},
                    ) from exc
                return parsed if isinstance(parsed, dict) else {}
            await asyncio.sleep(self.poll_interval_seconds)
        raise PipedreamActionAdapterError(
            "pipedream_event_response_timeout",
            detail={"timeout_seconds": self.timeout_seconds},
        )

    async def _response_store(self) -> Any:
        if not hasattr(self.bus, "_get_redis"):
            raise PipedreamActionAdapterError("pipedream_event_bus_response_store_unavailable")
        return await self.bus._get_redis()


def _normalize_capability(*, family: str, capability: str) -> str:
    return capability.removeprefix(f"{family}.").strip()


def _first_account(connections: list[dict[str, Any]], apps: tuple[str, ...]) -> dict[str, Any] | None:
    for wanted_app in apps:
        for connection in connections:
            app = str(connection.get("app") or "")
            if app == wanted_app and connection.get("healthy", True) and not connection.get("dead"):
                return connection
    return None


def _not_connected(*, family: str, capability: str, apps: tuple[str, ...]) -> dict[str, Any]:
    return {
        "status": "connector_not_connected",
        "family": family,
        "capability": capability,
        "expected_apps": list(apps),
        "external_connector_bound": False,
        "execution_mode": "pipedream_connect_action",
    }


def _public_account(account: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": account.get("id"),
        "app": account.get("app"),
        "name": account.get("name"),
        "healthy": bool(account.get("healthy", True)),
    }


def _bounded(value: Any, *, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, maximum))


def _extract_channel_name(query: str) -> str:
    patterns = (
        r"#([A-Za-z0-9][A-Za-z0-9_-]{1,80})",
        r"(?:canal|channel)\s+([A-Za-z0-9][A-Za-z0-9_-]{1,80})",
    )
    for pattern in patterns:
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    return ""


def _find_channel(items: Any, channel_name: str) -> dict[str, Any] | None:
    if not isinstance(items, list):
        return None
    normalized = channel_name.lstrip("#").lower()
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("name") or "").lower() == normalized or str(item.get("id") or "").lower() == normalized:
            return item
    return None


def _slack_channels(output: dict[str, Any]) -> list[dict[str, Any]]:
    ret = output.get("ret") if isinstance(output, dict) else None
    channels = ret.get("channels") if isinstance(ret, dict) else None
    return [
        {
            "id": channel.get("id"),
            "name": channel.get("name"),
            "is_member": channel.get("is_member"),
            "is_private": channel.get("is_private"),
            "num_members": channel.get("num_members"),
        }
        for channel in (channels if isinstance(channels, list) else [])
        if isinstance(channel, dict)
    ]


def _slack_messages(output: dict[str, Any]) -> list[dict[str, Any]]:
    ret = output.get("ret") if isinstance(output, dict) else None
    messages = ret.get("messages") if isinstance(ret, dict) else None
    return [
        {
            "user": message.get("user"),
            "text": _compact_text(str(message.get("text") or ""), 240),
            "ts": message.get("ts"),
            "type": message.get("type"),
        }
        for message in (messages if isinstance(messages, list) else [])
        if isinstance(message, dict)
    ]


def _mail_items(output: dict[str, Any]) -> list[dict[str, Any]]:
    ret = output.get("ret") if isinstance(output, dict) else None
    if isinstance(ret, dict):
        candidates = ret.get("messages") or ret.get("emails") or ret.get("value") or []
    else:
        candidates = ret if isinstance(ret, list) else []
    return [
        {
            "id": item.get("id") or item.get("messageId"),
            "subject": _compact_text(str(item.get("subject") or ""), 180),
            "sender": _compact_text(str(item.get("sender") or item.get("from") or ""), 180),
            "date": item.get("date") or item.get("receivedDateTime"),
            "snippet": _compact_text(str(item.get("snippet") or item.get("bodyPreview") or ""), 280),
        }
        for item in (candidates if isinstance(candidates, list) else [])
        if isinstance(item, dict)
    ]


def _gmail_labels(output: dict[str, Any]) -> list[dict[str, Any]]:
    ret = output.get("ret") if isinstance(output, dict) else None
    labels = ret.get("labels") if isinstance(ret, dict) else None
    return [
        {
            "id": label.get("id"),
            "name": label.get("name"),
            "type": label.get("type"),
            "messages_total": label.get("messagesTotal"),
            "messages_unread": label.get("messagesUnread"),
        }
        for label in (labels if isinstance(labels, list) else [])
        if isinstance(label, dict)
    ]


def _mentions_inbox(query: str) -> bool:
    normalized = query.lower()
    return any(token in normalized for token in ("inbox", "boîte", "boite", "réception", "reception"))


def _mentions_labels(query: str) -> bool:
    normalized = query.lower()
    return any(token in normalized for token in ("label", "libellé", "libelle", "étiquette", "etiquette"))


def _mail_provider_preference(query: str, *, provider_preference: str | None = None) -> tuple[str, ...]:
    normalized_preference = str(provider_preference or "").strip().lower().replace("-", "_")
    if normalized_preference == "gmail":
        return ("gmail", "microsoft_outlook")
    if normalized_preference == "microsoft_outlook":
        return ("microsoft_outlook", "gmail")

    normalized = _provider_hint_text(query).lower()
    mentions_gmail = any(token in normalized for token in ("gmail", "google mail"))
    mentions_outlook = any(
        token in normalized
        for token in ("outlook", "microsoft outlook", "microsoft 365", "office 365", "o365", "ms365")
    )
    if mentions_gmail and not mentions_outlook:
        return ("gmail", "microsoft_outlook")
    if _mentions_labels(query):
        return ("gmail", "microsoft_outlook")
    return ("microsoft_outlook", "gmail")


def _provider_hint_text(query: str) -> str:
    marker = "demande utilisateur:"
    normalized = query.lower()
    marker_index = normalized.rfind(marker)
    if marker_index >= 0:
        return query[marker_index + len(marker):].strip()
    return query


def _gmail_query(query: str) -> str:
    normalized = query.lower()
    filters = ["newer_than:30d"]
    if any(token in normalized for token in ("unread", "non lu", "non-lu", "pas lu")):
        filters.insert(0, "is:unread")
    if _mentions_inbox(query):
        filters.insert(0, "in:inbox")
    return " ".join(filters)


def _summary(output: dict[str, Any], *, item_count: int) -> str:
    exports = output.get("exports") if isinstance(output, dict) else None
    if isinstance(exports, dict) and exports.get("$summary"):
        return str(exports["$summary"])
    return f"{item_count} item(s) returned"


def _compact_error(error: Any) -> dict[str, Any]:
    if not isinstance(error, dict):
        return {"message": _compact_text(str(error), 240)}
    return {
        "name": error.get("name"),
        "message": _compact_text(str(error.get("message") or ""), 240),
    }


def _compact_text(value: str, limit: int) -> str:
    compacted = " ".join(value.split())
    if len(compacted) <= limit:
        return compacted
    return f"{compacted[: max(0, limit - 3)]}..."
