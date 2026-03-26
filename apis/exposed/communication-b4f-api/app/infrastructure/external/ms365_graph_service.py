"""MS Graph API client — OAuth2 + mail/calendar data access."""

from typing import Optional, Tuple, List, Any, Dict
from datetime import datetime, timezone
import os

import httpx
import structlog

logger = structlog.get_logger(__name__)

MS365_CLIENT_ID = os.environ.get("MS365_CLIENT_ID", "")
MS365_CLIENT_SECRET = os.environ.get("MS365_CLIENT_SECRET", "")
MS365_TENANT_ID = os.environ.get("MS365_TENANT_ID", "")
MS365_REDIRECT_URI = os.environ.get("MS365_REDIRECT_URI", "")
WEBHOOK_API_KEY = os.environ.get("WEBHOOK_API_KEY", "")

AUTHORITY = f"https://login.microsoftonline.com/{MS365_TENANT_ID}"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = [
    "Mail.Read",
    "Mail.Send",
    "Calendars.ReadWrite",
    "User.Read",
    "offline_access",
]


class MS365GraphService:
    """Client for Microsoft Graph API operations.

    Handles OAuth2 flow, token management, and data fetching
    for emails and calendar events via delegated permissions.
    """

    def __init__(self) -> None:
        self._client_id = MS365_CLIENT_ID
        self._client_secret = MS365_CLIENT_SECRET
        self._redirect_uri = MS365_REDIRECT_URI

    # ── OAuth2 Flow ──────────────────────────────────────────────────

    def build_auth_url(self, state: Optional[str] = None) -> str:
        """Build the Microsoft OAuth2 authorization URL using proper URL encoding."""
        from urllib.parse import urlencode
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "scope": " ".join(SCOPES),
            "response_mode": "query",
        }
        if state:
            params["state"] = state
        query = urlencode(params)
        return f"{AUTHORITY}/oauth2/v2.0/authorize?{query}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access + refresh tokens."""
        logger.info("ms365_exchanging_code", client_id=self._client_id, redirect_uri=self._redirect_uri)
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
            if resp.status_code >= 400:
                body = resp.text
                logger.error("ms365_token_exchange_failed", status=resp.status_code, body=body)
                raise Exception(f"Token exchange failed ({resp.status_code}): {body[:500]}")
            data = resp.json()
            logger.info("ms365_token_exchanged", scopes=data.get("scope"))
            return data

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token."""
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

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get the authenticated user's profile from MS Graph."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_BASE}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

    # ── Emails ───────────────────────────────────────────────────────

    async def get_emails_batched(
        self,
        access_token: str,
        delta_token: Optional[str] = None,
        top: int = 50,
    ):
        """Async generator that yields (page_messages, page_number, total_so_far)
        one page at a time, keeping memory usage constant regardless of mailbox size.
        """
        use_delta = bool(delta_token)
        self._last_delta_token: Optional[str] = None
        self._last_sync_was_delta = use_delta

        if delta_token:
            url = delta_token
        else:
            url = (
                f"{GRAPH_BASE}/me/messages"
                f"?$select=subject,bodyPreview,body,from,toRecipients,ccRecipients,"
                f"receivedDateTime,isRead,importance,hasAttachments,conversationId,"
                f"parentFolderId"
                f"&$top={top}"
                f"&$orderby=receivedDateTime desc"
            )

        page = 0
        total = 0

        async with httpx.AsyncClient(timeout=60.0) as client:
            while url:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                data = resp.json()

                messages = data.get("value", [])
                page += 1
                total += len(messages)

                logger.info("ms365_emails_page", page=page, items=len(messages), total_so_far=total)

                yield messages, page, total

                url = data.get("@odata.nextLink")

                if "@odata.deltaLink" in data:
                    self._last_delta_token = data["@odata.deltaLink"]

    async def acquire_delta_token(self, access_token: str) -> Optional[str]:
        """After an initial full sync, page through a delta query to obtain a
        delta token for future incremental syncs."""
        if self._last_delta_token:
            return self._last_delta_token
        if getattr(self, "_last_sync_was_delta", False):
            return None
        try:
            delta_url: Optional[str] = (
                f"{GRAPH_BASE}/me/mailFolders/inbox/messages/delta"
                f"?$select=subject,bodyPreview,body,from,toRecipients,ccRecipients,"
                f"receivedDateTime,isRead,importance,hasAttachments,conversationId,"
                f"parentFolderId"
                f"&$top=1"
            )
            async with httpx.AsyncClient(timeout=30.0) as client:
                while delta_url:
                    resp = await client.get(
                        delta_url,
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    resp.raise_for_status()
                    ddata = resp.json()
                    delta_url = ddata.get("@odata.nextLink")
                    if "@odata.deltaLink" in ddata:
                        self._last_delta_token = ddata["@odata.deltaLink"]
                        delta_url = None
            logger.info("ms365_delta_token_acquired", has_delta=bool(self._last_delta_token))
        except Exception as e:
            logger.warning("ms365_delta_token_failed", error=str(e))
        return self._last_delta_token

    async def get_emails(
        self,
        access_token: str,
        delta_token: Optional[str] = None,
        top: int = 50,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Legacy wrapper — accumulates all pages in memory.
        Prefer get_emails_batched() for large mailboxes.
        """
        all_messages: List[Dict[str, Any]] = []
        last_page = 0
        async for page_msgs, _page, _total in self.get_emails_batched(access_token, delta_token, top):
            all_messages.extend(page_msgs)
            last_page = _page
        new_delta = await self.acquire_delta_token(access_token)

        logger.info("ms365_emails_fetched", count=len(all_messages), pages=last_page, has_delta=bool(new_delta))
        return all_messages, new_delta

    async def get_calendar_events(
        self,
        access_token: str,
        delta_token: Optional[str] = None,
        top: int = 50,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch calendar events using delta query for incremental sync."""
        if delta_token:
            url = delta_token
        else:
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            start_dt = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            end_dt = (now + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
            url = (
                f"{GRAPH_BASE}/me/calendarView/delta"
                f"?startDateTime={start_dt}&endDateTime={end_dt}"
                f"&$select=subject,body,location,start,end,isAllDay,organizer,"
                f"attendees,showAs,isCancelled,recurrence,onlineMeeting"
                f"&$top={top}"
            )

        all_events: List[Dict[str, Any]] = []
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

    # ── Sending Emails ───────────────────────────────────────────────

    async def send_mail(
        self,
        access_token: str,
        subject: str,
        body_content: str,
        to_recipients: List[str],
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        body_type: str = "html",
    ) -> Dict[str, str]:
        """Compose and send a new email via MS Graph."""
        message: Dict[str, Any] = {
            "subject": subject,
            "body": {"contentType": body_type, "content": body_content},
            "toRecipients": [{"emailAddress": {"address": email}} for email in to_recipients],
        }
        if cc_recipients:
            message["ccRecipients"] = [{"emailAddress": {"address": email}} for email in cc_recipients]
        if bcc_recipients:
            message["bccRecipients"] = [{"emailAddress": {"address": email}} for email in bcc_recipients]

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GRAPH_BASE}/me/sendMail",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"message": message, "saveToSentItems": "true"},
            )
            resp.raise_for_status()
            logger.info("ms365_mail_sent", subject=subject)
            return {"status": "sent"}

    async def reply_mail(
        self,
        access_token: str,
        message_id: str,
        comment: str,
        reply_all: bool = False,
    ) -> Dict[str, str]:
        """Reply to an existing email (or reply all)."""
        action = "replyAll" if reply_all else "reply"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GRAPH_BASE}/me/messages/{message_id}/{action}",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"message": {"body": {"contentType": "html", "content": comment}}},
            )
            resp.raise_for_status()
            logger.info(f"ms365_mail_{action}", original_id=message_id)
            return {"status": "sent"}

    async def forward_mail(
        self,
        access_token: str,
        message_id: str,
        to_recipients: List[str],
        comment: str = "",
    ) -> Dict[str, str]:
        """Forward an existing email."""
        payload: Dict[str, Any] = {
            "toRecipients": [{"emailAddress": {"address": email}} for email in to_recipients],
        }
        if comment:
            payload["comment"] = comment

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GRAPH_BASE}/me/messages/{message_id}/forward",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            logger.info("ms365_mail_forwarded", original_id=message_id)
            return {"status": "sent"}

    # ── Webhook Subscriptions ────────────────────────────────────────

    async def create_webhook_subscription(
        self,
        access_token: str,
        resource: str,
        callback_url: str,
        expiration_minutes: int = 4230,
    ) -> Dict[str, Any]:
        """Create a MS Graph change notification subscription."""
        from datetime import timedelta
        expiration = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GRAPH_BASE}/subscriptions",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={
                    "changeType": "created,updated,deleted",
                    "notificationUrl": callback_url,
                    "resource": resource,
                    "expirationDateTime": expiration.isoformat() + "Z",
                    "clientState": WEBHOOK_API_KEY,
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
    ) -> Dict[str, Any]:
        """Renew a MS Graph webhook subscription."""
        from datetime import timedelta
        expiration = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)

        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{GRAPH_BASE}/subscriptions/{subscription_id}",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"expirationDateTime": expiration.isoformat() + "Z"},
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("ms365_webhook_renewed", subscription_id=subscription_id)
            return data

    # ── Token Management Helpers ─────────────────────────────────────

    async def ensure_valid_token(self, access_token: str, refresh_token: str, expires_at: datetime) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Check if token is valid. If expired, refresh it. On refresh failure, re-raise."""
        if datetime.now(timezone.utc) >= expires_at:
            new_tokens = await self.refresh_access_token(refresh_token)
            return new_tokens["access_token"], new_tokens
        return access_token, None
