"""Domain exceptions for Opportunity API."""


class OpportunityNotFoundError(Exception):
    """Raised when an opportunity cannot be found for the active tenant."""


class OpportunityLineItemNotFoundError(Exception):
    """Raised when an opportunity product line cannot be found for the active tenant."""


class QuoteNotFoundError(Exception):
    """Raised when a quote cannot be found for the active tenant."""
