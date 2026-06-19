"""Behavioral Analyzer compatibility facade.

The provider-backed analysis belongs to the internal Agent Backend. The B4F
keeps this adapter only for legacy imports and delegates through its internal
service client.
"""


class BehavioralAnalyzer:
    """Delegate behavioral analysis to the internal Agent Backend."""

    def __init__(self, client_map_client):
        self.client_map_client = client_map_client

    async def analyze(
        self,
        contact_id: str,
        tenant_id: str,
        forward_headers: dict | None = None,
    ) -> dict:
        result = await self.client_map_client.analyze_behavior(
            contact_id,
            forward_headers=forward_headers,
        )
        return result.get("behavioral_profile", result)
