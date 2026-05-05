"""
Integration tests pentru /auth endpoints.
DB-ul este mockat complet — nu necesită PostgreSQL.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

with patch("sqlalchemy.create_engine", return_value=MagicMock()):
    from main import app

from app.database import get_db
from app.auth import get_current_user, hash_password


# ── Fake objects ──────────────────────────────────────────────────────────────

@dataclass
class FakeUser:
    id: int = 1
    email: str = "test@example.com"
    full_name: str = "Test User"
    role: str = "sales_rep"
    hashed_password: str = ""


def _make_db(existing_user=None):
    """Returnează un mock DB session configurat pentru auth endpoints."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = existing_user

    def fake_refresh(obj):
        """Simulează ce face PostgreSQL la INSERT: populează id și role default."""
        if not getattr(obj, "id", None):
            obj.id = 1
        if not getattr(obj, "role", None):
            obj.role = "sales_rep"

    mock_db.refresh.side_effect = fake_refresh
    return mock_db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_overrides():
    """Curăță dependency overrides după fiecare test."""
    yield
    app.dependency_overrides.clear()


# ── POST /auth/register ───────────────────────────────────────────────────────

class TestRegister:
    def test_register_returns_201(self):
        app.dependency_overrides[get_db] = lambda: _make_db(existing_user=None)
        client = TestClient(app)
        response = client.post("/auth/register", json={
            "email": "new@example.com",
            "full_name": "New User",
            "password": "password123",
        })
        assert response.status_code == 201

    def test_register_response_has_correct_fields(self):
        app.dependency_overrides[get_db] = lambda: _make_db(existing_user=None)
        client = TestClient(app)
        response = client.post("/auth/register", json={
            "email": "maria@techcorp.ro",
            "full_name": "Maria Ionescu",
            "password": "pass123",
        })
        data = response.json()
        assert data["email"] == "maria@techcorp.ro"
        assert data["full_name"] == "Maria Ionescu"
        assert "hashed_password" not in data
        assert "id" in data

    def test_register_duplicate_email_returns_400(self):
        existing = FakeUser(email="dup@example.com")
        app.dependency_overrides[get_db] = lambda: _make_db(existing_user=existing)
        client = TestClient(app)
        response = client.post("/auth/register", json={
            "email": "dup@example.com",
            "full_name": "User",
            "password": "pass123",
        })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_sets_access_token_cookie(self):
        app.dependency_overrides[get_db] = lambda: _make_db(existing_user=None)
        client = TestClient(app)
        response = client.post("/auth/register", json={
            "email": "cookie@example.com",
            "full_name": "Cookie User",
            "password": "pass123",
        })
        assert "access_token" in response.cookies

    def test_register_invalid_email_returns_422(self):
        client = TestClient(app)
        response = client.post("/auth/register", json={
            "email": "not-an-email",
            "full_name": "User",
            "password": "pass123",
        })
        assert response.status_code == 422


# ── POST /auth/login ──────────────────────────────────────────────────────────

class TestLogin:
    def test_login_wrong_email_returns_401(self):
        """Userul nu există în DB."""
        app.dependency_overrides[get_db] = lambda: _make_db(existing_user=None)
        client = TestClient(app)
        response = client.post("/auth/login", json={
            "email": "notfound@example.com",
            "password": "password",
        })
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_wrong_password_returns_401(self):
        fake_user = FakeUser(hashed_password=hash_password("correct_password"))
        app.dependency_overrides[get_db] = lambda: _make_db(existing_user=fake_user)
        client = TestClient(app)
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrong_password",
        })
        assert response.status_code == 401

    def test_login_correct_credentials_returns_200(self):
        fake_user = FakeUser(hashed_password=hash_password("mypassword"))
        app.dependency_overrides[get_db] = lambda: _make_db(existing_user=fake_user)
        client = TestClient(app)
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "mypassword",
        })
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    def test_login_sets_cookie(self):
        fake_user = FakeUser(hashed_password=hash_password("mypassword"))
        app.dependency_overrides[get_db] = lambda: _make_db(existing_user=fake_user)
        client = TestClient(app)
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "mypassword",
        })
        assert "access_token" in response.cookies


# ── POST /auth/logout ─────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_returns_200(self):
        client = TestClient(app)
        response = client.post("/auth/logout")
        assert response.status_code == 200

    def test_logout_message(self):
        client = TestClient(app)
        response = client.post("/auth/logout")
        assert "Logged out" in response.json()["message"]


# ── GET /auth/me ──────────────────────────────────────────────────────────────

class TestMe:
    def test_me_without_token_returns_401(self):
        client = TestClient(app)
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_me_with_valid_user_returns_200(self):
        fake_user = FakeUser()
        app.dependency_overrides[get_current_user] = lambda: fake_user
        client = TestClient(app)
        response = client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["role"] == "sales_rep"
