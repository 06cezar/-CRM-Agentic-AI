import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from datetime import datetime

with patch("sqlalchemy.create_engine", return_value=MagicMock()):
    from main import app

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
class FakeICP:
    id: int = 1
    user_id: int = 1
    raw_inputs: dict = None
    structured_data: dict = None
    is_active: bool = True
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

def _make_db():
    mock_db = MagicMock()
    
    def fake_refresh(obj):
        if not getattr(obj, "id", None):
            obj.id = 1
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now()
        if not getattr(obj, "updated_at", None):
            obj.updated_at = datetime.now()
            
    mock_db.refresh.side_effect = fake_refresh
    return mock_db

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_dependencies():
    app.dependency_overrides[get_current_user] = lambda: FakeUser()
    yield
    app.dependency_overrides.clear()

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_create_icp():
    mock_db = _make_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    
    client = TestClient(app)
    payload = {
        "target_persona": "VPs of Sales",
        "target_company": "Tech Series B",
        "core_pain": "Pipeline leaks",
        "trigger_event": "New funding",
        "value_proposition": "AI Automation"
    }
    
    response = client.post("/icp/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["raw_inputs"] == payload
    assert data["user_id"] == 1
    assert data["is_active"] is True
    
    # Verify DB calls
    assert mock_db.add.called
    assert mock_db.commit.called

def test_get_active_icp():
    mock_db = _make_db()
    fake_icp = FakeICP(raw_inputs={"target_persona": "Founders"})
    mock_db.query.return_value.filter.return_value.first.return_value = fake_icp
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    client = TestClient(app)
    response = client.get("/icp/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["raw_inputs"]["target_persona"] == "Founders"

def test_get_icp_empty():
    mock_db = _make_db()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    client = TestClient(app)
    response = client.get("/icp/")
    
    assert response.status_code == 200
    assert response.json() is None

def test_create_icp_validation_error():
    client = TestClient(app)
    # Missing fields
    payload = {
        "target_persona": "VPs of Sales"
    }
    response = client.post("/icp/", json=payload)
    assert response.status_code == 422
