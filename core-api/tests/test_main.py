from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys

# Mock DB before importing app so CI doesn't need a real PostgreSQL
with patch("sqlalchemy.create_engine", return_value=MagicMock()):
    from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_python_version():
    assert sys.version_info >= (3, 11)
