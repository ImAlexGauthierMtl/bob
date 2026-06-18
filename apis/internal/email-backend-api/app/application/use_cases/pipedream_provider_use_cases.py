"""Pipedream provider use cases."""

from typing import Any, Awaitable, Callable, Optional, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class PipedreamClientPort(Protocol):
    async def create_connect_token(self, external_user_id: str, **kwargs: Any) -> dict[str, Any]:
        ...

    async def list_accounts(self, external_user_id: str, app: Optional[str] = None) -> list[dict[str, Any]]:
        ...

    async def list_apps(self, query: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
        ...

    async def delete_account(self, account_id: str) -> bool:
        ...

    async def run_action(self, action_id: str, external_user_id: str, configured_props: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        ...

    async def close(self) -> None:
        ...


SettingLookup = Callable[[str, Any], Awaitable[Optional[dict[str, Any]]]]
BuildExternalUserId = Callable[[str, str, str, Optional[str]], str]
DefaultScopeFor = Callable[[str], str]
ClientFactory = Callable[[], PipedreamClientPort]
SettingsGetter = Callable[[], Any]
CredentialSetter = Callable[[str, str, str, str, str], None]


_APP_SLUG_ALIASES = {
    "microsoft-outlook": "microsoft_outlook",
    "google-drive": "google_drive",
    "google-sheets": "google_sheets",
    "zoho-crm": "zoho_crm",
    "dynamics-crm": "microsoft_dynamics_365",
}


class PipedreamProviderUseCases:
    def __init__(
        self,
        *,
        client_factory: ClientFactory,
        setting_lookup: SettingLookup,
        build_external_user_id: BuildExternalUserId,
        default_scope_for: DefaultScopeFor,
        get_settings: SettingsGetter,
        set_credentials: CredentialSetter,
    ) -> None:
        self.client_factory = client_factory
        self.setting_lookup = setting_lookup
        self.build_external_user_id = build_external_user_id
        self.default_scope_for = default_scope_for
        self.get_settings = get_settings
        self.set_credentials = set_credentials

    async def external_user_id(self, user: dict[str, Any], integration_key: str, request_headers: Any = None) -> str:
        tenant_id = user.get("tenant_id") or "default"
        user_id = user["user_id"]
        org_id = user.get("active_organization_id")

        setting = await self.setting_lookup(integration_key, request_headers)
        if setting:
            scope = setting.get("scope_mode", self.default_scope_for(integration_key))
            return self.build_external_user_id(tenant_id, scope, user_id, org_id)
        return self.build_external_user_id(tenant_id, self.default_scope_for(integration_key), user_id, org_id)

    def app_slug(self, integration_key: str) -> str:
        key = (integration_key or "").replace("~connector.", "").strip()
        return _APP_SLUG_ALIASES.get(key, key.replace("-", "_"))

    @staticmethod
    def integration_key_from_app_slug(app_slug: str) -> str:
        return (app_slug or "").replace("_", "-")

    @staticmethod
    def connect_link_with_app(connect_link_url: str, app: str) -> str:
        parts = urlsplit(connect_link_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["app"] = app
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    @staticmethod
    def normalize_account(raw: dict[str, Any]) -> dict[str, Any]:
        app = raw.get("app") or {}
        return {
            "id": raw.get("id"),
            "app": app.get("name_slug"),
            "name": raw.get("name") or app.get("name"),
            "healthy": bool(raw.get("healthy", True)),
            "dead": raw.get("dead"),
            "created_at": raw.get("created_at"),
            "updated_at": raw.get("updated_at"),
        }

    async def create_token(
        self,
        user: dict[str, Any],
        integration_key: str,
        request_headers: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        external_user_id = await self.external_user_id(user, integration_key, request_headers)
        client = self.client_factory()
        try:
            return await client.create_connect_token(external_user_id, **kwargs)
        finally:
            await client.close()

    async def connect_url(
        self,
        user: dict[str, Any],
        integration_key: str,
        redirect_uri: str,
        request_headers: Any = None,
    ) -> dict[str, str]:
        app = self.app_slug(integration_key)
        token_payload = await self.create_token(
            user,
            integration_key,
            request_headers,
            success_redirect_uri=redirect_uri,
            error_redirect_uri=redirect_uri,
        )
        return {"url": self.connect_link_with_app(token_payload["connect_link_url"], app), "app": app}

    async def list_connections(self, user: dict[str, Any], integration_key: Optional[str], request_headers: Any = None) -> list[dict[str, Any]]:
        external_user_id = await self.external_user_id(user, integration_key or "", request_headers)
        app = self.app_slug(integration_key) if integration_key else None
        client = self.client_factory()
        try:
            accounts = await client.list_accounts(external_user_id, app=app)
            return [self.normalize_account(account) for account in accounts]
        finally:
            await client.close()

    async def delete_connection(self, connection_id: str) -> bool:
        client = self.client_factory()
        try:
            return await client.delete_account(connection_id)
        finally:
            await client.close()

    async def list_integrations(self, query: Optional[str] = None) -> list[dict[str, Any]]:
        client = self.client_factory()
        try:
            apps = await client.list_apps(query=query)
            return [
                {
                    "id": app.get("id") or app.get("name_slug"),
                    "key": self.integration_key_from_app_slug(app.get("name_slug")),
                    "name": app.get("name") or app.get("name_slug"),
                    "description": app.get("description"),
                    "iconUrl": app.get("img_src"),
                    "status": "active",
                }
                for app in apps
                if app.get("name_slug")
            ]
        finally:
            await client.close()

    async def run_action(
        self,
        user: dict[str, Any],
        action_id: str,
        integration_key: str,
        configured_props: dict[str, Any],
        request_headers: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        external_user_id = await self.external_user_id(user, integration_key, request_headers)
        client = self.client_factory()
        try:
            return await client.run_action(action_id, external_user_id, configured_props, **kwargs)
        finally:
            await client.close()

    def get_config(self) -> dict[str, Any]:
        current = self.get_settings()
        has_secret = bool(current.pipedream_client_secret)
        return {
            "client_id": current.pipedream_client_id or "",
            "project_id": current.pipedream_project_id or "",
            "environment": current.pipedream_environment,
            "api_url": current.pipedream_api_url,
            "configured": bool(current.pipedream_client_id and has_secret and current.pipedream_project_id),
            "secret_configured": has_secret,
        }

    def update_config(self, data: dict[str, Any]) -> dict[str, Any]:
        current = self.get_settings()
        incoming_secret = (data.get("client_secret") or "").strip()
        is_masked = incoming_secret and set(incoming_secret) <= {"*", " "}
        effective_secret = current.pipedream_client_secret if not incoming_secret or is_masked else incoming_secret
        self.set_credentials(
            data["client_id"],
            effective_secret,
            data["project_id"],
            data["environment"],
            data["api_url"],
        )
        return {
            "client_id": data["client_id"],
            "project_id": data["project_id"],
            "environment": data["environment"],
            "api_url": data["api_url"],
            "configured": bool(data["client_id"] and effective_secret and data["project_id"]),
            "secret_configured": bool(effective_secret),
            "message": "Pipedream configuration updated successfully",
        }
