"""MS365 Sync Service — orchestrates sync via HTTP client to email~backend-api."""

from app.infrastructure.clients.email_client import connection_client, email_crud_client, event_crud_client


class MS365SyncService:
    """Sync orchestration — business logic stays here, CRUD via HTTP."""

    def __init__(self, forward_headers=None):
        self._headers = forward_headers

    async def sync_emails(self, connection: dict) -> int:
        """Sync emails from MS365 via Graph API, persist via backend."""
        raise NotImplementedError()

    async def sync_calendar(self, connection: dict) -> int:
        """Sync calendar from MS365 via Graph API, persist via backend."""
        raise NotImplementedError()

    async def handle_webhook_notification(self, notifications: list) -> None:
        """Handle webhook notification from MS Graph."""
        raise NotImplementedError()
