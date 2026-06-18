"""Bob Control Center application use cases."""
from typing import Any


class BccUseCases:
    """Application boundary for BCC operations.

    BCC still has a broad legacy CRUD surface. This boundary keeps HTTP routes
    thin while the operation adapter preserves the existing behavior.
    """

    def __init__(self, operations: Any) -> None:
        self.operations = operations

    def __getattr__(self, name: str) -> Any:
        return getattr(self.operations, name)
