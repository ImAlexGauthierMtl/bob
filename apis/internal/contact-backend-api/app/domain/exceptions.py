"""Domain exceptions for Contact API."""


class ContactNotFoundError(Exception):
    """Raised when a contact cannot be found for the active tenant."""
