"""Domain exceptions for Product API."""


class ProductNotFoundError(Exception):
    """Raised when a product cannot be found for the active tenant."""
