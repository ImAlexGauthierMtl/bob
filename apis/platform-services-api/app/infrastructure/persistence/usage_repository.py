"""Usage Repository — placeholder."""


class UsageRepository:
    """Placeholder for Usage Repository."""
    
    def __init__(self, db):
        self.db = db
    
    def record_usage(self, user_id: str, resource_type: str, quantity: int) -> None:
        """Record resource usage."""
        raise NotImplementedError()
    
    def get_usage(self, user_id: str, resource_type: str) -> dict:
        """Get usage stats."""
        raise NotImplementedError()
