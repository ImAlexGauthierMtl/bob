"""Domain entities for the Bob Cloud local stub."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityDecision:
    capability: str
    status: str
    reason_code: str | None = None
    remaining: int | None = None
    limit: int | None = None

    def to_payload(self) -> dict:
        payload = {"capability": self.capability, "status": self.status}
        if self.reason_code:
            payload["reason_code"] = self.reason_code
        if self.remaining is not None:
            payload["remaining"] = self.remaining
        if self.limit is not None:
            payload["limit"] = self.limit
        return payload

class StubResourceNotFound(Exception):
    """Raised when a local Bob Cloud stub resource does not exist."""
