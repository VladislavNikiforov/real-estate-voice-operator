"""Tests for the pipeline orchestrator."""
import pytest
from unittest.mock import AsyncMock, patch


class TestHandleSendInvoice:
    @pytest.mark.asyncio
    async def test_returns_pipeline_result(self, invoice_params_en):
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            from llm.orchestrator import handle_send_invoice
            result = await handle_send_invoice(invoice_params_en)
        assert result.success is True
        assert result.invoice_number is not None
        assert "John Smith" in result.message or "sent" in result.message.lower()

    @pytest.mark.asyncio
    async def test_invoice_number_format(self, invoice_params_lv):
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            from llm.orchestrator import handle_send_invoice
            result = await handle_send_invoice(invoice_params_lv)
        assert result.invoice_number.startswith("INV-")

    @pytest.mark.asyncio
    async def test_missing_required_field_returns_error(self):
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            from llm.orchestrator import handle_send_invoice
            result = await handle_send_invoice({
                "client_name": "John",
                # missing client_email, property_id, amount, language
            })
        assert result.success is False

    @pytest.mark.asyncio
    async def test_openclaw_failure_still_succeeds(self, invoice_params_en):
        """Pipeline returns success even if OpenClaw is unreachable."""
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            from llm.orchestrator import handle_send_invoice
            result = await handle_send_invoice(invoice_params_en)
        assert result.success is True   # still succeeds, just queued


class TestHandleSendReminder:
    @pytest.mark.asyncio
    async def test_returns_success(self, reminder_params):
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            from llm.orchestrator import handle_send_reminder
            result = await handle_send_reminder(reminder_params)
        assert result.success is True


class TestHandleFollowUp:
    @pytest.mark.asyncio
    async def test_returns_success(self, follow_up_params):
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            from llm.orchestrator import handle_follow_up
            result = await handle_follow_up(follow_up_params)
        assert result.success is True


class TestHandleRequestDocuments:
    @pytest.mark.asyncio
    async def test_returns_success(self, request_documents_params):
        with patch("llm.orchestrator._post_to_openclaw", new=AsyncMock(return_value=False)):
            from llm.orchestrator import handle_request_documents
            result = await handle_request_documents(request_documents_params)
        assert result.success is True
