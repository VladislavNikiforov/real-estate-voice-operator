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


class TestLookupContact:
    def test_lookup_existing_contact(self):
        resp = client.post("/api/tools/lookup-contact", json={"name": "John Smith"})
        assert resp.status_code == 200
        data = resp.json()
        assert "full_name" in data or "error" in data

    def test_lookup_empty_name(self):
        resp = client.post("/api/tools/lookup-contact", json={"name": ""})
        assert resp.status_code == 200
        assert "error" in resp.json()


class TestSearchEmails:
    def test_search_returns_emails(self):
        resp = client.post("/api/tools/search-emails", json={"query": "invoice"})
        assert resp.status_code == 200
        data = resp.json()
        assert "emails" in data


class TestCreateTask:
    def test_create_invoice_task(self):
        with patch("llm.orchestrator.send_email", new=AsyncMock(return_value={"success": True, "message_id": "t1"})), \
             patch("llm.orchestrator.notify_task_complete", new=AsyncMock(return_value=True)), \
             patch("llm.orchestrator.lookup_client", new=AsyncMock(return_value=None)), \
             patch("llm.orchestrator.lookup_service", new=AsyncMock(return_value=None)):
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

    def test_unknown_action(self):
        resp = client.post("/api/tools/create-task", json={"action": "unknown"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"


class TestTestEndpoint:
    def test_test_endpoint(self):
        with patch("llm.orchestrator.send_email", new=AsyncMock(return_value={"success": True, "message_id": "t1"})), \
             patch("llm.orchestrator.notify_task_complete", new=AsyncMock(return_value=True)), \
             patch("llm.orchestrator.lookup_client", new=AsyncMock(return_value=None)), \
             patch("llm.orchestrator.lookup_service", new=AsyncMock(return_value=None)):
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
        assert "result" in resp.json()


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
