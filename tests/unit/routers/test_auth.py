"""Unit tests for authentication helpers (password hashing, JWT tokens)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt

from backend.app.routers.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from backend.app.config import get_settings

settings = get_settings()


class TestPasswordHashing:
    """Test bcrypt password hashing and verification."""

    def test_hash_password_returns_bcrypt_hash(self):
        hashed = hash_password("testpassword123")
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60

    def test_hash_password_different_salts(self):
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2  # Different salts each time

    def test_verify_password_correct(self):
        hashed = hash_password("MySecurePass!")
        assert verify_password("MySecurePass!", hashed) is True

    def test_verify_password_wrong(self):
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty_string(self):
        hashed = hash_password("notempty")
        assert verify_password("", hashed) is False

    def test_hash_password_unicode(self):
        hashed = hash_password("p\u00e4ssw\u00f6rd")
        assert verify_password("p\u00e4ssw\u00f6rd", hashed) is True

    def test_hash_password_max_length(self):
        # bcrypt truncates at 72 bytes
        long_pw = "a" * 72
        hashed = hash_password(long_pw)
        assert verify_password(long_pw, hashed) is True


class TestAccessToken:
    """Test JWT access token creation and structure."""

    def test_creates_valid_jwt(self):
        token = create_access_token({"sub": "user-123", "role": "admin"})
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_default_expiration(self):
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        # Should expire within configured minutes (default 30) +/- 5 seconds tolerance
        delta = exp - now
        expected = timedelta(minutes=settings.access_token_expire_minutes)
        assert abs(delta.total_seconds() - expected.total_seconds()) < 5

    def test_custom_expiration(self):
        token = create_access_token(
            {"sub": "user-123"},
            expires_delta=timedelta(hours=2),
        )
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = exp - now
        assert abs(delta.total_seconds() - 7200) < 5

    def test_does_not_mutate_input(self):
        data = {"sub": "user-123"}
        create_access_token(data)
        assert "exp" not in data
        assert "type" not in data


class TestRefreshToken:
    """Test JWT refresh token creation and structure."""

    def test_creates_refresh_type(self):
        token = create_refresh_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["type"] == "refresh"
        assert payload["sub"] == "user-123"

    def test_longer_expiration_than_access(self):
        access = create_access_token({"sub": "user-123"})
        refresh = create_refresh_token({"sub": "user-123"})

        access_payload = jwt.decode(access, settings.secret_key, algorithms=[settings.algorithm])
        refresh_payload = jwt.decode(refresh, settings.secret_key, algorithms=[settings.algorithm])

        assert refresh_payload["exp"] > access_payload["exp"]

    def test_does_not_mutate_input(self):
        data = {"sub": "user-456"}
        create_refresh_token(data)
        assert "exp" not in data
        assert "type" not in data


class TestTokenSecurity:
    """Test token security properties."""

    def test_wrong_secret_rejects(self):
        token = create_access_token({"sub": "user-123"})
        with pytest.raises(Exception):
            jwt.decode(token, "wrong-secret-key", algorithms=[settings.algorithm])

    def test_wrong_algorithm_rejects(self):
        token = create_access_token({"sub": "user-123"})
        with pytest.raises(Exception):
            jwt.decode(token, settings.secret_key, algorithms=["HS384"])

    def test_access_and_refresh_distinguishable(self):
        data = {"sub": "user-123"}
        access = create_access_token(data)
        refresh = create_refresh_token(data)

        access_payload = jwt.decode(access, settings.secret_key, algorithms=[settings.algorithm])
        refresh_payload = jwt.decode(refresh, settings.secret_key, algorithms=[settings.algorithm])

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
        assert access != refresh
