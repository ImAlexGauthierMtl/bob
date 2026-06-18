"""MS365 provider application use cases."""
from typing import Any


class MS365ProviderUseCases:
    """Application boundary for the legacy MS365 provider surface."""

    def __init__(self, operations: Any) -> None:
        self.operations = operations

    def __getattr__(self, name: str) -> Any:
        return getattr(self.operations, name)
