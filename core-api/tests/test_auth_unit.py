"""
Unit tests pentru app/auth.py — hash, verify, JWT.
Nu necesită DB sau TestClient.
"""

import pytest
from jose import jwt, JWTError
from datetime import datetime

from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)


# ── hash_password ─────────────────────────────────────────────────────────────

class TestHashPassword:
    def test_differs_from_plain(self):
        assert hash_password("secret123") != "secret123"

    def test_bcrypt_format(self):
        h = hash_password("secret123")
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_same_input_produces_different_hashes(self):
        """bcrypt este salt-based — același parola dă hash-uri diferite."""
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert h1 != h2

    def test_non_empty_result(self):
        h = hash_password("x")
        assert len(h) > 20


# ── verify_password ───────────────────────────────────────────────────────────

class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password("mypassword")
        assert verify_password("wrongpassword", h) is False

    def test_empty_password_returns_false(self):
        h = hash_password("mypassword")
        assert verify_password("", h) is False

    def test_case_sensitive(self):
        h = hash_password("Password")
        assert verify_password("password", h) is False

    def test_whitespace_matters(self):
        h = hash_password("pass word")
        assert verify_password("password", h) is False


# ── create_access_token ───────────────────────────────────────────────────────

class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token({"sub": "1"})
        assert isinstance(token, str)
        assert len(token) > 10

    def test_decodable_with_correct_secret(self):
        token = create_access_token({"sub": "42"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "42"

    def test_has_expiry_field(self):
        token = create_access_token({"sub": "1"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_expiry_is_in_future(self):
        token = create_access_token({"sub": "1"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["exp"] > datetime.utcnow().timestamp()

    def test_wrong_secret_raises_jwt_error(self):
        token = create_access_token({"sub": "1"})
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret", algorithms=[ALGORITHM])

    def test_extra_fields_preserved_in_payload(self):
        token = create_access_token({"sub": "1", "role": "admin", "custom": "value"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["role"] == "admin"
        assert payload["custom"] == "value"

    def test_sub_field_is_string(self):
        token = create_access_token({"sub": "99"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "99"
