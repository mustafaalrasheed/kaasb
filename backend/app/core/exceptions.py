"""
Kaasb Platform - Custom Exception Classes
Domain exceptions decoupled from HTTP — services raise these,
and the global exception handler maps them to HTTP responses.
"""

from typing import Any, Optional


class KaasbError(Exception):
    """Base exception for all Kaasb domain errors."""

    def __init__(self, message: str = "An error occurred", *, details: Optional[Any] = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(KaasbError):
    """Resource not found (maps to 404)."""

    def __init__(self, resource: str = "Resource", identifier: Any = None) -> None:
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} with id '{identifier}' not found"
        super().__init__(detail)
        self.resource = resource


class ConflictError(KaasbError):
    """Duplicate or conflicting resource (maps to 409)."""
    pass


class ForbiddenError(KaasbError):
    """User lacks permission for this action (maps to 403)."""
    pass


class BadRequestError(KaasbError):
    """Invalid input or business rule violation (maps to 400)."""
    pass


class UnauthorizedError(KaasbError):
    """Authentication failure (maps to 401)."""
    pass


class RateLimitError(KaasbError):
    """Too many requests (maps to 429)."""
    pass


class ExternalServiceError(KaasbError):
    """External service (payment gateway, etc.) failed (maps to 502)."""
    pass
