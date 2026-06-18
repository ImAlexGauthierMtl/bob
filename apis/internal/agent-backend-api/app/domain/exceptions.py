"""Domain exceptions for Agent API."""


class CapabilityNotFoundError(Exception):
    """Raised when a capability definition cannot be found."""


class ContactNotFoundError(Exception):
    """Raised when a contact cannot be found for the active tenant."""


class ClientMapNotFoundError(Exception):
    """Raised when a client map cannot be found for the active tenant."""


class GoldenNoteNotFoundError(Exception):
    """Raised when a golden note cannot be found for the active tenant."""


class TrainingSessionNotFoundError(Exception):
    """Raised when a training session cannot be found for the active user."""


class TrainingNoteNotFoundError(Exception):
    """Raised when a training note cannot be found for the active user."""


class TrainingMissingElementNotFoundError(Exception):
    """Raised when a missing training element cannot be found for the active user."""


class InvalidBobVoiceError(Exception):
    """Raised when a requested Bob voice is not available."""


class InvalidBobToneError(Exception):
    """Raised when a requested Bob tone is not available."""
