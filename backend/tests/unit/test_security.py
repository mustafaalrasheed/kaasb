"""Unit tests for core security utilities."""

import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password_returns_hash(self):
        hashed = hash_password("TestPassword1!")
        assert hashed != "TestPassword1!"
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        hashed = hash_password("MyPassword123!")
        assert verify_password("MyPassword123!", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("MyPassword123!")
        assert verify_password("WrongPassword!", hashed) is False

    def test_different_hashes_for_same_password(self):
        hash1 = hash_password("SamePassword1!")
        hash2 = hash_password("SamePassword1!")
        assert hash1 != hash2  # bcrypt uses random salt


class TestJWT:
    """Tests for JWT token creation and decoding."""

    def test_create_and_decode_access_token(self):
        data = {"sub": "test-user-id", "role": "client", "tv": 0}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload["sub"] == "test-user-id"
        assert payload["role"] == "client"
        assert payload["type"] == "access"

    def test_token_contains_expiry(self):
        token = create_access_token({"sub": "123"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_invalid_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401
