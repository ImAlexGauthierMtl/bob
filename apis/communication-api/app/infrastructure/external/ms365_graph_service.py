"""MS365 Graph Service — placeholder."""


class MS365GraphService:
    """Placeholder for MS365 Graph integration."""
    
    def build_auth_url(self, state: str) -> str:
        """Build OAuth2 auth URL."""
        raise NotImplementedError()
    
    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange auth code for tokens."""
        raise NotImplementedError()
    
    async def get_user_profile(self, access_token: str) -> dict:
        """Get user profile from MS Graph."""
        raise NotImplementedError()
    
    async def ensure_valid_token(self, access_token: str, refresh_token: str, expires_at: str) -> tuple:
        """Ensure access token is valid, refresh if needed."""
        raise NotImplementedError()
    
    async def send_mail(self, **kwargs) -> dict:
        """Send email via MS Graph."""
        raise NotImplementedError()
    
    async def reply_mail(self, **kwargs) -> dict:
        """Reply to email via MS Graph."""
        raise NotImplementedError()
    
    async def forward_mail(self, **kwargs) -> dict:
        """Forward email via MS Graph."""
        raise NotImplementedError()
