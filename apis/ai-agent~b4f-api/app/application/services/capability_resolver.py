"""Capability resolver — B4F version using HTTP client.

Resolution is now delegated to agent~backend-api.
This service provides convenience methods for Bob's agent logic.
"""

import structlog
from app.infrastructure.clients.agent_client import capability_client

logger = structlog.get_logger(__name__)


class CapabilityResolver:
    """Resolves capabilities for a user via the backend API."""

    async def can(self, user_id: str, capability_code: str, forward_headers: dict = None) -> bool:
        """Check if a user has a specific capability."""
        try:
            result = await capability_client.check(capability_code, forward_headers=forward_headers)
            return result.get("granted", False)
        except Exception as e:
            logger.warning("capability_check_failed", code=capability_code, error=str(e))
            return False

    async def get_all_capabilities(self, user_id: str, forward_headers: dict = None) -> dict:
        """Get all capabilities with their resolved status for a user."""
        try:
            return await capability_client.get_user_capabilities(user_id, forward_headers=forward_headers)
        except Exception as e:
            logger.warning("capabilities_fetch_failed", user_id=user_id, error=str(e))
            return {"user_id": user_id, "agent_mode": "standard", "trust_score": 0.0, "capabilities": []}

    def get_agent_mode(self, trust_score: float) -> str:
        """Determine Bob's execution mode based on trust_score."""
        if trust_score >= 0.6:
            return "auto"
        elif trust_score >= 0.3:
            return "approval"
        return "suggest"
