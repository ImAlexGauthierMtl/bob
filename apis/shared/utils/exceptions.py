"""Custom exceptions for APIs."""


class APIError(Exception):
    """Base API error."""

    def __init__(self, message: str, status_code: int = 400, details: str = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class NotFoundError(APIError):
    """Resource not found (404)."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(f"{resource} not found: {resource_id}", status_code=404)


class ConflictError(APIError):
    """Conflict error (409)."""

    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class ForbiddenError(APIError):
    """Forbidden (403)."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class UnauthorizedError(APIError):
    """Unauthorized (401)."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)
