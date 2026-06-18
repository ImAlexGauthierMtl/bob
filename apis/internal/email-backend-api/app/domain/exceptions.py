"""Domain exceptions for Email API."""


class ConnectionNotFoundError(Exception):
    """Raised when an MS365 connection cannot be found."""


class ConnectionAlreadyExistsError(Exception):
    """Raised when a user already has an MS365 connection."""


class EmailNotFoundError(Exception):
    """Raised when a synced email cannot be found."""


class EventNotFoundError(Exception):
    """Raised when a synced event cannot be found."""


class IntegrationSettingNotFoundError(Exception):
    """Raised when an integration setting cannot be found."""


class SmartLabelNotFoundError(Exception):
    """Raised when a smart label cannot be found."""


class SmartLabelDuplicateError(Exception):
    """Raised when a smart label name already exists in its context."""


class SmartLabelDeleteError(Exception):
    """Raised when a smart label cannot be deleted."""
