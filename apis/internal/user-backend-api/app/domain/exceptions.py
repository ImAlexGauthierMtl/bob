"""Domain exceptions for User API."""


class UserNotFoundError(Exception):
    """Raised when a user cannot be found."""


class UserAlreadyExistsError(Exception):
    """Raised when creating a user with an existing email."""


class TenantNotFoundError(Exception):
    """Raised when a tenant cannot be found."""


class TenantSlugAlreadyExistsError(Exception):
    """Raised when creating or updating a tenant with an existing slug."""


class RoleNotFoundError(Exception):
    """Raised when a role cannot be found."""


class RoleAlreadyExistsError(Exception):
    """Raised when creating a role with an existing name."""


class SystemRoleDeletionError(Exception):
    """Raised when attempting to delete a system role."""
