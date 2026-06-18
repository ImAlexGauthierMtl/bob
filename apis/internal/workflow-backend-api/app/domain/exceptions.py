"""Domain exceptions for Workflow API."""


class WorkflowNotFoundError(Exception):
    """Raised when a workflow cannot be found for the active tenant."""


class WorkflowStepNotFoundError(Exception):
    """Raised when a workflow step cannot be found."""


class WorkflowExecutionNotFoundError(Exception):
    """Raised when a workflow execution cannot be found."""
