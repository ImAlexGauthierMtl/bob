"""User Repository — placeholder."""


class UserRepository:
    """Placeholder for User Repository."""
    
    def __init__(self, db):
        self.db = db
    
    def get_by_id(self, user_id: str, tenant_id: str):
        """Get user by ID."""
        raise NotImplementedError()
    
    def get_by_email(self, email: str, tenant_id: str):
        """Get user by email."""
        raise NotImplementedError()
