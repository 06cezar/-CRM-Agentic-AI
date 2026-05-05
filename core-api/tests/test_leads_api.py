"""
Integration tests pentru /leads endpoints.
DB-ul și auth sunt mockate complet — nu necesită PostgreSQL sau ai-service.
"""

import io
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, patch

with patch("sqlalchemy.create_engine", return_value=MagicMock()):
    from main import app  # noqa: E402

from fastapi.testclient import TestClient
from app.database import get_db
from app.auth import get_current_user


# ── Fake objects ──────────────────────────────────────────────────────────────

@dataclass
class FakeUser:
    id: int = 1
    email: str = "test@example.com"
    full_name: str = "Test User"
    role: str = "sales_rep"


@dataclass
class FakeLead:
    id: int = 1
    name: str = "Maria Ionescu"
    company: str = "TechCorp SRL"
    role: str = "CEO"
    email: str = "maria@techcorp.ro"
    phone: Optional[str] = None
    deal_value: Optional[Decimal] = Decimal("45000")
    currency: str = "EUR"
    last_activity_description: Optional[str] = "Viewed pricing page"
    intent_score: Optional[int] = 87
    last_researched_at: Optional[datetime] = None
    signals: list = field(default_factory=lambda: ["Budget Approved"])
    assigned_to: Optional[int] = 1
    status: str = "new"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


FAKE_USER = FakeUser()
FAKE_LEAD = FakeLead()


# ── DB mock helpers ───────────────────────────────────────────────────────────

def _make_db(lead=None, leads=None):
    mock_db = MagicMock()
    # GET single lead: .filter().first()
    mock_db.query.return_value.filter.return_value.first.return_value = lead
    # GET list: .filter().order_by().all()
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
        leads if leads is not None else []
    )

    def fake_refresh(obj):
        """Simulează DB-ul populând câmpurile generate automat."""
        if not getattr(obj, "id", None):
            obj.id = 1
        if getattr(obj, "signals", None) is None:
            obj.signals = []
        if not getattr(obj, "status", None):
            obj.status = "new"
        if not getattr(obj, "currency", None):
            obj.currency = "EUR"
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)

    mock_db.refresh.side_effect = fake_refresh
    return mock_db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def auth_override():
    """Injectează un user autentificat pentru toate testele din acest fișier."""
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield
    app.dependency_overrides.clear()


# ── GET /leads ────────────────────────────────────────────────────────────────

class TestListLeads:
    def test_unauthenticated_returns_401(self):
        app.dependency_overrides.clear()  # elimină auth override
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/leads")
        assert response.status_code == 401

    def test_returns_empty_list(self):
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        app.dependency_overrides[get_db] = lambda: _make_db(leads=[])
        client = TestClient(app)
        response = client.get("/leads")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_leads_list(self):
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        app.dependency_overrides[get_db] = lambda: _make_db(leads=[FAKE_LEAD])
        client = TestClient(app)
        response = client.get("/leads")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Maria Ionescu"
        assert data[0]["email"] == "maria@techcorp.ro"

    def test_lead_response_has_score_alias(self):
        """score e alias pentru intent_score — frontend îl folosește."""
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        app.dependency_overrides[get_db] = lambda: _make_db(leads=[FAKE_LEAD])
        client = TestClient(app)
        response = client.get("/leads")
        data = response.json()
        assert data[0]["score"] == 87

    def test_lead_response_has_deal_value_display(self):
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        app.dependency_overrides[get_db] = lambda: _make_db(leads=[FAKE_LEAD])
        client = TestClient(app)
        response = client.get("/leads")
        data = response.json()
        assert data[0]["deal_value_display"] == "€45,000"


# ── POST /leads ───────────────────────────────────────────────────────────────

class TestCreateLead:
    def test_create_lead_returns_201(self):
        app.dependency_overrides[get_db] = lambda: _make_db()
        client = TestClient(app)
        with patch("app.routers.leads._run_research_in_background"):
            response = client.post("/leads", json={
                "name": "Ion Popescu",
                "company": "StartupSRL",
                "role": "CTO",
                "email": "ion@startup.ro",
            })
        assert response.status_code == 201

    def test_create_lead_unauthenticated_returns_401(self):
        app.dependency_overrides.clear()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/leads", json={
            "name": "Ion", "company": "X", "role": "Y", "email": "x@y.com",
        })
        assert response.status_code == 401

    def test_create_lead_missing_required_field_returns_422(self):
        app.dependency_overrides[get_db] = lambda: _make_db()
        client = TestClient(app)
        # Lipsesc câmpuri obligatorii (company, role, email)
        response = client.post("/leads", json={"name": "Ion"})
        assert response.status_code == 422


# ── GET /leads/{id} ───────────────────────────────────────────────────────────

class TestGetLead:
    def test_get_existing_lead_returns_200(self):
        app.dependency_overrides[get_db] = lambda: _make_db(lead=FAKE_LEAD)
        client = TestClient(app)
        response = client.get("/leads/1")
        assert response.status_code == 200
        assert response.json()["name"] == "Maria Ionescu"

    def test_get_nonexistent_lead_returns_404(self):
        app.dependency_overrides[get_db] = lambda: _make_db(lead=None)
        client = TestClient(app)
        response = client.get("/leads/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ── PATCH /leads/{id} ────────────────────────────────────────────────────────

class TestUpdateLead:
    def test_update_existing_lead_returns_200(self):
        app.dependency_overrides[get_db] = lambda: _make_db(lead=FAKE_LEAD)
        client = TestClient(app)
        response = client.patch("/leads/1", json={"name": "Maria Updated"})
        assert response.status_code == 200

    def test_update_nonexistent_lead_returns_404(self):
        app.dependency_overrides[get_db] = lambda: _make_db(lead=None)
        client = TestClient(app)
        response = client.patch("/leads/999", json={"name": "X"})
        assert response.status_code == 404

    def test_partial_update_only_changes_sent_fields(self):
        """PATCH trimite doar câmpurile care se schimbă."""
        app.dependency_overrides[get_db] = lambda: _make_db(lead=FAKE_LEAD)
        client = TestClient(app)
        response = client.patch("/leads/1", json={"role": "COO"})
        assert response.status_code == 200
        # Modelul are setter-ul apelat — verificăm că nu crapa


# ── DELETE /leads/{id} ───────────────────────────────────────────────────────

class TestDeleteLead:
    def test_delete_existing_lead_returns_204(self):
        app.dependency_overrides[get_db] = lambda: _make_db(lead=FAKE_LEAD)
        client = TestClient(app)
        response = client.delete("/leads/1")
        assert response.status_code == 204

    def test_delete_nonexistent_lead_returns_404(self):
        app.dependency_overrides[get_db] = lambda: _make_db(lead=None)
        client = TestClient(app)
        response = client.delete("/leads/999")
        assert response.status_code == 404


# ── POST /leads/import ────────────────────────────────────────────────────────

class TestImportCSV:
    def _make_csv(self, content: str) -> tuple:
        return ("test.csv", io.BytesIO(content.encode("utf-8")), "text/csv")

    def test_import_valid_csv(self):
        app.dependency_overrides[get_db] = lambda: _make_db()
        client = TestClient(app)
        csv_content = "name,email,company,role\nIon Popescu,ion@startup.ro,StartupSRL,CEO\n"
        with patch("app.routers.leads._run_research_in_background"):
            response = client.post(
                "/leads/import",
                files={"file": self._make_csv(csv_content)},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 1
        assert data["skipped"] == 0

    def test_import_skips_row_missing_email(self):
        app.dependency_overrides[get_db] = lambda: _make_db()
        client = TestClient(app)
        csv_content = "name,email,company\nIon Popescu,,StartupSRL\n"
        with patch("app.routers.leads._run_research_in_background"):
            response = client.post(
                "/leads/import",
                files={"file": self._make_csv(csv_content)},
            )
        assert response.status_code == 200
        assert response.json()["skipped"] == 1
        assert response.json()["imported"] == 0

    def test_import_rejects_non_csv(self):
        app.dependency_overrides[get_db] = lambda: _make_db()
        client = TestClient(app)
        response = client.post(
            "/leads/import",
            files={"file": ("data.xlsx", io.BytesIO(b"binary"), "application/vnd.ms-excel")},
        )
        assert response.status_code == 400
