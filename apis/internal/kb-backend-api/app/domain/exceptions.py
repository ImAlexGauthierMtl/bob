"""Domain exceptions for KB API."""


class CategoryNotFoundError(Exception):
    """Raised when a category cannot be found for the active tenant."""


class ArticleNotFoundError(Exception):
    """Raised when an article cannot be found for the active tenant."""
