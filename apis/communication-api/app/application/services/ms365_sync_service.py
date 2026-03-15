"""MS365 Sync Service — placeholder."""


class MS365SyncService:
    """Placeholder for MS365 sync functionality."""
    
    def __init__(self, db):
        self.db = db
    
    async def sync_emails(self, connection) -> int:
        """Sync emails from MS365."""
        raise NotImplementedError()
    
    async def sync_calendar(self, connection) -> int:
        """Sync calendar from MS365."""
        raise NotImplementedError()
    
    async def handle_webhook_notification(self, notifications: list) -> None:
        """Handle webhook notification from MS Graph."""
        raise NotImplementedError()
