"""Tests for clawforce.auth module."""

from datetime import datetime, timedelta, timezone

from clawforce.auth import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """hash_password should return bcrypt hash."""
        password = "secure_password_123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2")
        assert len(hashed) == 60

    def test_hash_different_each_time(self):
        """Same password should produce different hashes (salt)."""
        password = "test_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_verify_password_correct(self):
        """verify_password should return True for correct password."""
        password = "my_secret_password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password should return False for incorrect password."""
        password = "correct_password"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self):
        """verify_password should handle empty passwords."""
        password = ""
        hashed = hash_password(password)

        assert verify_password("", hashed) is True
        assert verify_password("nonempty", hashed) is False

    def test_verify_password_unicode(self):
        """verify_password should handle unicode passwords."""
        password = "密码🔐пароль"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("different", hashed) is False


class TestJWTTokens:
    """Tests for JWT token functions."""

    def test_create_access_token(self):
        """create_access_token should return valid JWT."""
        token = create_access_token(sub="user-123")

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2

    def test_create_token_with_role(self):
        """create_access_token should include role in payload."""
        token = create_access_token(sub="user-123", role="super_admin")
        payload = decode_token(token)

        assert payload["role"] == "super_admin"

    def test_decode_token_valid(self):
        """decode_token should return payload for valid token."""
        token = create_access_token(sub="user-456", role="admin")
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "user-456"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_decode_token_invalid(self):
        """decode_token should return None for invalid token."""
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_decode_token_malformed(self):
        """decode_token should return None for malformed token."""
        payload = decode_token("not-a-jwt")
        assert payload is None

    def test_decode_token_empty(self):
        """decode_token should return None for empty token."""
        payload = decode_token("")
        assert payload is None

    def test_token_expiration_included(self):
        """Token should include expiration time."""
        token = create_access_token(sub="user-123")
        payload = decode_token(token)

        assert "exp" in payload
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)

        assert exp_time > now

    def test_token_roundtrip(self):
        """Token should survive encode/decode roundtrip."""
        original_sub = "test-user-789"
        original_role = "viewer"

        token = create_access_token(sub=original_sub, role=original_role)
        payload = decode_token(token)

        assert payload["sub"] == original_sub
        assert payload["role"] == original_role


class TestTokenExpiration:
    """Tests for token expiration handling."""

    def test_default_expiration(self, monkeypatch):
        """Token should have default 24-hour expiration."""
        token = create_access_token(sub="user")
        payload = decode_token(token)

        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)

        time_until_expiry = exp_time - now
        assert timedelta(hours=23) < time_until_expiry < timedelta(hours=25)
