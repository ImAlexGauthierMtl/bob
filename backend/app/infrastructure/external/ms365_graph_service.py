"""MS Graph API client — OAuth2 + mail/calendar data access."""

from typing import Optional, Tuple, List
from datetime import datetime, timezone

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

# MS Graph API endpoints
AUTHORITY = f"https://login.microsoftonline.com/{settings.ms365_tenant_id}"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Read", "Calendars.Read", "User.Read", "offline_access"]


class MS365GraphService:
    """Client for Microsoft Graph API operations.

    Handles OAuth2 flow, token management, and data fetching
    for emails and calendar events via delegated permissions.
    """

    def __init__(self) -> None:
        self._client_id = settings.ms365_client_id
        self._client_secret = settings.ms365_client_secret
        self._redirect_uri = settings.ms365_redirect_uri

    # ── OAuth2 Flow ──────────────────────────────────────────────────

    def build_auth_url(self, state: Optional[str] = None) -> str:
        """Build the Microsoft OAuth2 authorization URL."""
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "scope": " ".join(SCOPES),
            "response_mode": "query",
        }
        if state:
            params["state"] = state
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{AUTHORITY}/oauth2/v2.0/authorize?{query}"

    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for access + refresh tokens.

        Returns dict with: access_token, refresh_token,
        expires_in, scope, token_type.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{AUTHORITY}/oauth2/v2.0/token",
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                    "scope": " ".join(SCOPES),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("ms365_token_exchanged", scopes=data.get("scope"))
            return data

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh an expired access token.

        Returns dict with: access_token, refresh_token,
        expires_in, scope.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{AUTHORITY}/oauth2/v2.0/token",
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": " ".join(SCOPES),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("ms365_token_refreshed")
            return data

    # ── User Profile ─────────────────────────────────────────────────

    async def get_user_profile(self, access_token: str) -> dict:
        """Get the authenticated user's profile from MS Graph.

        Returns dict with: id, mail, displayName, userPrincipalName.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_BASE}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

    # ── Emails ───────────────────────────────────────────────────────

    async def get_emails(
        self,
        access_token: str,
        delta_token: Optional[str] = None,
        top: int = 50,
    ) -> Tuple[List[dict], Optional[str]]:
        """Fetch emails using delta query for incremental sync.

        Returns (emails, new_delta_token).
        If delta_token is provided, fetches only changes since last sync.
        """
        if delta_token:
            url = delta_token
        else:
            url = (
                f"{GRAPH_BASE}/me/mailFolders/inbox/messages/delta"
                f"?$select=subject,bodyPreview,body,from,toRecipients,ccRecipients,"
                f"receivedDateTime,isRead,importance,hasAttachments,conversationId,"
                f"parentFolderId"
                f"&$top={top}"
                f"&$orderby=receivedDateTime desc"
            )

        all_messages: List[dict] = []
        new_delta: Optional[str] = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                data = resp.json()

                messages = data.get("value", [])
                all_messages.extend(messages)

                # Follow @odata.nextLink for pagination
                url = data.get("@odata.nextLink")

                # Capture deltaLink when pagination is done
                if "@odata.deltaLink" in data:
                    new_delta = data["@odata.deltaLink"]

        logger.info("ms365_emails_fetched", count=len(all_messages), has_delta=bool(new_delta))
        return all_messages, new_delta

    async def get_calendar_events(
        self,
        access_token: str,
        delta_token: Optional[str] = None,
        top: int = 50,
    ) -> Tuple[List[dict], Optional[str]]:
        """Fetch calendar events using delta query for incremental sync.

        Returns (events, new_delta_token).
        """
        if delta_token:
            url = delta_token
        else:
            url = (
                f"{GRAPH_BASE}/me/calendarView/delta"
                f"?$select=subject,body,location,start,end,isAllDay,organizer,"
                f"attendees,showAs,isCancelled,recurrence,onlineMeeting"
                f"&$top={top}"
            )

        all_events: List[dict] = []
        new_delta: Optional[str] = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                data = resp.json()

                events = data.get("value", [])
                all_events.extend(events)

                url = data.get("@odata.nextLink")

                if "@odata.deltaLink" in data:
                    new_delta = data["@odata.deltaLink"]

        logger.info("ms365_events_fetched", count=len(all_events), has_delta=bool(new_delta))
        return all_events, new_delta

    # ── Webhook Subscriptions ────────────────────────────────────────

    async def create_webhook_subscription(
        self,
        access_token: str,
        resource: str,
        callback_url: str,
        expiration_minutes: int = 4230,  # ~3 days max for mail
    ) -> dict:
        """Create a MS Graph change notification subscription.

        Args:
            resource: e.g. "me/mailFolders/inbox/messages" or "me/events"
            callback_url: HTTPS endpoint that receives notifications
            expiration_minutes: Subscription lifetime (max 4230 for mail)

        Returns subscription dict with id, expirationDateTime.
        """
        from datetime import timedelta
        expiration = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GRAPH_BASE}/subscriptions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "changeType": "created,updated,deleted",
                    "notificationUrl": callback_url,
                    "resource": resource,
                    "expirationDateTime": expiration.isoformat() + "Z",
                    "clientState": settings.webhook_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("ms365_webhook_created", resource=resource, subscription_id=data.get("id"))
            return data

    async def renew_webhook_subscription(
        self,
        access_token: str,
        subscription_id: str,
        expiration_minutes: int = 4230,
    ) -> dict:
        """Renew a MS Graph webhook subscription."""
        from datetime import timedelta
        expiration = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)

        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{GRAPH_BASE}/subscriptions/{subscription_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "expirationDateTime": expiration.isoformat() + "Z",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("ms365_webhook_renewed", subscription_id=subscription_id)
            return data

    # ── Token Management Helpers ─────────────────────────────────────

    async def ensure_valid_token(self, access_token: str, refresh_token: str, expires_at: datetime) -> Tuple[str, Optional[dict]]:
        """Check if token is valid. If expired, refresh it.

        Returns (valid_access_token, new_token_data_or_None).
        """
        if datetime.now(timezone.utc) >= expires_at:
            new_tokens = await self.refresh_access_token(refresh_token)
            return new_tokens["access_token"], new_tokens
        return access_token, None
