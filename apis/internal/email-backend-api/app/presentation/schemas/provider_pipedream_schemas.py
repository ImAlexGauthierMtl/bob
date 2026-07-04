"""Pipedream provider schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class PipedreamTokenRequest(BaseModel):
    app: Optional[str] = None
    integration_key: Optional[str] = None
    success_redirect_uri: Optional[str] = None
    error_redirect_uri: Optional[str] = None
    webhook_uri: Optional[str] = None
    allowed_origins: Optional[list[str]] = None


class PipedreamTokenResponse(BaseModel):
    token: str
    expires_at: str
    connect_link_url: str


class PipedreamConnectUrlResponse(BaseModel):
    url: str
    app: str


class PipedreamConnectionResponse(BaseModel):
    id: str
    app: Optional[str] = None
    name: Optional[str] = None
    healthy: bool = True
    dead: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"extra": "allow"}


class PipedreamConnectionListResponse(BaseModel):
    items: list[PipedreamConnectionResponse]


class PipedreamPageInfo(BaseModel):
    count: Optional[int] = None
    total_count: Optional[int] = None
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None


class PipedreamIntegrationResponse(BaseModel):
    id: str
    key: str
    name: str
    iconUrl: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"


class PipedreamIntegrationListResponse(BaseModel):
    items: list[PipedreamIntegrationResponse]
    page_info: Optional[PipedreamPageInfo] = None


class PipedreamToolResponse(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    component_type: Optional[str] = None
    version: Optional[str] = None
    annotations: dict[str, Any] = Field(default_factory=dict)
    configurable_props_count: int = 0


class PipedreamToolListResponse(BaseModel):
    items: list[PipedreamToolResponse]
    page_info: Optional[PipedreamPageInfo] = None


class PipedreamActionRunRequest(BaseModel):
    action_key: Optional[str] = None
    connection_id: Optional[str] = None
    input: dict[str, Any] = Field(default_factory=dict)
    version: Optional[str] = None
    dynamic_props_id: Optional[str] = None
    stash_id: Optional[str] = None


class PipedreamActionRunResponse(BaseModel):
    success: bool
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class PipedreamWebhookPayload(BaseModel):
    event_type: Optional[str] = None
    type: Optional[str] = None
    external_user_id: Optional[str] = None
    account_id: Optional[str] = None
    app: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)


class PipedreamConfigRequest(BaseModel):
    client_id: str
    client_secret: Optional[str] = None
    project_id: str
    environment: str = "development"
    api_url: str = "https://api.pipedream.com/v1"


class PipedreamConfigResponse(BaseModel):
    client_id: str
    project_id: str
    environment: str
    api_url: str
    configured: bool
    secret_configured: bool = False
    message: Optional[str] = None
