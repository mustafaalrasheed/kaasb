"""Unit tests for custom exception classes."""

from app.core.exceptions import (
    NotFoundError, ConflictError, ForbiddenError,
    BadRequestError, UnauthorizedError, KaasbError,
)


class TestCustomExceptions:
    def test_not_found_error_message(self):
        err = NotFoundError("Job", "abc-123")
        assert "Job" in err.message
        assert "abc-123" in err.message

    def test_not_found_error_default(self):
        err = NotFoundError("Contract")
        assert err.message == "Contract not found"

    def test_conflict_error(self):
        err = ConflictError("Email already registered")
        assert err.message == "Email already registered"

    def test_forbidden_error(self):
        err = ForbiddenError("Admin access required")
        assert err.message == "Admin access required"

    def test_bad_request_error(self):
        err = BadRequestError("Invalid input")
        assert err.message == "Invalid input"

    def test_unauthorized_error(self):
        err = UnauthorizedError("Token expired")
        assert err.message == "Token expired"

    def test_base_error_with_details(self):
        err = KaasbError("Something failed", details={"field": "email"})
        assert err.details == {"field": "email"}
