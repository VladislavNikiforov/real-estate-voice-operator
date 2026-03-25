"""Tests for Vapi webhook parsing + server endpoints."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)


def _vapi_payload(tool: str, args: dict) -> dict:
    return {
        "message": {
            "type": "tool-calls",
            "toolCallList": [{
                "id": "test_call_001",
                "type": "function",
                "function": {"name": tool, "arguments": args},
            }]
        }
    }


class TestHealthEndpoint:
    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestTestEndpoint:
    def test_test_endpoint_exists(self):
        # Even with no OpenClaw, /api/test should return 200
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


class TestVapiToolCall:
    def test_vapi_endpoint_returns_results_key(self):
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            resp = client.post("/api/vapi/tool-call", json=_vapi_payload("send_invoice", {
                "client_name": "Jānis",
                "client_email": "j@j.lv",
                "property_id": "apt-3",
                "amount": 85000,
                "language": "lv",
            }))
        assert resp.status_code == 200
        assert "results" in resp.json()

    def test_vapi_non_tool_call_returns_empty_results(self):
        resp = client.post("/api/vapi/tool-call", json={
            "message": {"type": "assistant-request"}
        })
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_vapi_unknown_tool_returns_error_message(self):
        resp = client.post("/api/vapi/tool-call", json=_vapi_payload("unknown_tool", {}))
        assert resp.status_code == 200
        result_text = resp.json()["results"][0]["result"]
        assert result_text  # non-empty — something is said back

    def test_vapi_bad_json_returns_400(self):
        resp = client.post(
            "/api/vapi/tool-call",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_result_contains_tool_call_id(self):
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            resp = client.post("/api/vapi/tool-call", json=_vapi_payload("send_reminder", {
                "client_name": "Anna",
                "client_email": "a@a.lv",
                "language": "lv",
            }))
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["toolCallId"] == "test_call_001"
