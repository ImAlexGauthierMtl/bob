"""Domain exceptions for Org API."""


class OrganizationNotFoundError(Exception):
    """Raised when an organization cannot be found for the active tenant."""


class DepartmentNotFoundError(Exception):
    """Raised when a department cannot be found for the active tenant."""
