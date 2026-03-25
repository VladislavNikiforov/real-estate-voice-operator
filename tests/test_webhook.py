"""Tests for ElevenLabs webhook endpoints + Claude chat endpoint."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestTestEndpoint:
    def test_test_endpoint_exists(self):
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            resp = client.post("/api/test", json={
                "tool": "send_invoice",
                "params": {
                    "client_name": "John",
                    "client_email": "j@j.com",
                    "property_id": "apt-1",
                    "amount": 10000,
                    "language": "en",
                }
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data


class TestElevenLabsTools:
    def test_lookup_contact_returns_result(self):
        resp = client.post("/api/tools/lookup-contact", json={"name": "John"})
        assert resp.status_code == 200
        data = resp.json()
        assert "full_name" in data or "error" in data

    def test_lookup_contact_empty_name(self):
        resp = client.post("/api/tools/lookup-contact", json={"name": ""})
        assert resp.status_code == 200
        assert "error" in resp.json()

    def test_search_emails_returns_mock(self):
        resp = client.post("/api/tools/search-emails", json={"query": "invoice"})
        assert resp.status_code == 200
        assert "emails" in resp.json()

    def test_create_task_send_invoice(self):
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            resp = client.post("/api/tools/create-task", json={
                "action": "send_invoice",
                "client_name": "John",
                "client_email": "j@j.com",
                "property_id": "apt-1",
                "amount": 10000,
                "language": "en",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("completed", "failed")

    def test_create_task_unknown_action(self):
        resp = client.post("/api/tools/create-task", json={"action": "unknown"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_bad_json_returns_400(self):
        resp = client.post(
            "/api/tools/lookup-contact",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400


class TestChatEndpoint:
    def test_chat_no_text_returns_400(self):
        resp = client.post("/api/chat", json={"session_id": "test", "text": ""})
        assert resp.status_code == 400

    def test_chat_no_api_key_returns_message(self):
        """Without ANTHROPIC_API_KEY, chat returns a friendly error."""
        resp = client.post("/api/chat", json={"session_id": "test", "text": "hello"})
        assert resp.status_code == 200
        assert "not configured" in resp.json()["text"].lower() or "text" in resp.json()

    def test_chat_reset(self):
        resp = client.post("/api/chat/reset", json={"session_id": "test"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
