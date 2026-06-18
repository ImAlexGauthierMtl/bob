"""Domain exceptions for Activity API."""


class ActivityNotFoundError(Exception):
    """Raised when an activity cannot be found for the active tenant."""
