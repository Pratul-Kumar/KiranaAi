"""
Smoke tests for ZnShop API.
Run from project root:  cd backend && pytest ../tests/test_api.py -v
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="module")
def client():
    with patch("app.db.supabase.create_client", return_value=MagicMock()):
        from src.main import app
        with TestClient(app) as c:
            yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_webhook_verify_correct_token(client):
    with patch("app.api.v1.whatsapp.settings") as mock_settings:
        mock_settings.WHATSAPP_VERIFY_TOKEN = "test_token"
        r = client.get(
            "/api/v1/whatsapp/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": "test_token", "hub.challenge": "abc123"},
        )
        assert r.status_code == 200
        assert r.text == "abc123"


def test_webhook_verify_wrong_token(client):
    with patch("app.api.v1.whatsapp.settings") as mock_settings:
        mock_settings.WHATSAPP_VERIFY_TOKEN = "test_token"
        r = client.get(
            "/api/v1/whatsapp/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "abc"},
        )
        assert r.status_code == 403


def test_admin_login_wrong_password(client):
    with patch("app.api.v1.admin.settings") as mock_settings:
        mock_settings.ADMIN_EMAIL = "admin@znshop.local"
        mock_settings.ADMIN_PASSWORD = "correct"
        r = client.post("/api/v1/admin/login", json={"email": "admin@znshop.local", "password": "wrong"})
        assert r.status_code == 401


def test_admin_stores_requires_auth(client):
    r = client.get("/api/v1/admin/stores")
    assert r.status_code == 401


def test_docs_available(client):
    r = client.get("/docs")
    assert r.status_code == 200


def test_public_alerts_returns_json(client):
    r = client.get("/api/v1/alerts")
    # Returns 200 with {"alerts": [...]} even with mocked Supabase
    assert r.status_code == 200
    assert "alerts" in r.json()


def test_khata_add_requires_auth(client):
    r = client.post("/api/v1/admin/khata/add", json={
        "customer_id": "00000000-0000-0000-0000-000000000001",
        "amount": 100.0,
        "action": "credit_given",
    })
    assert r.status_code == 401
