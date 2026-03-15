"""User entity — placeholder."""


class User:
    """Placeholder User entity."""
    
    def __init__(self, id: str, email: str, **kwargs):
        self.id = id
        self.email = email
        for key, value in kwargs.items():
            setattr(self, key, value)
