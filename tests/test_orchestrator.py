"""Tests for the pipeline orchestrator."""
import pytest
from unittest.mock import AsyncMock, patch


def _mock_gmail():
    """Mock both Gmail send and Notion lookups."""
    return [
        patch("llm.orchestrator.send_email", new=AsyncMock(return_value={"success": True, "message_id": "test123"})),
        patch("llm.orchestrator.notify_task_complete", new=AsyncMock(return_value=True)),
        patch("llm.orchestrator.lookup_client", new=AsyncMock(return_value=None)),
        patch("llm.orchestrator.lookup_service", new=AsyncMock(return_value=None)),
    ]


class TestHandleSendInvoice:
    @pytest.mark.asyncio
    async def test_returns_pipeline_result(self, invoice_params_en):
        with _mock_gmail()[0], _mock_gmail()[1], _mock_gmail()[2], _mock_gmail()[3]:
            from llm.orchestrator import handle_send_invoice
            result = await handle_send_invoice(invoice_params_en)
        assert result.success is True
        assert result.invoice_number is not None

    @pytest.mark.asyncio
    async def test_invoice_number_format(self, invoice_params_lv):
        with _mock_gmail()[0], _mock_gmail()[1], _mock_gmail()[2], _mock_gmail()[3]:
            from llm.orchestrator import handle_send_invoice
            result = await handle_send_invoice(invoice_params_lv)
        assert result.invoice_number.startswith("INV-")

    @pytest.mark.asyncio
    async def test_missing_email_returns_error(self):
        with _mock_gmail()[0], _mock_gmail()[1], _mock_gmail()[2], _mock_gmail()[3]:
            from llm.orchestrator import handle_send_invoice
            result = await handle_send_invoice({
                "client_name": "John",
                # no email, no Notion fallback
            })
        assert result.success is False


class TestHandleSendReminder:
    @pytest.mark.asyncio
    async def test_returns_success(self, reminder_params):
        with _mock_gmail()[0], _mock_gmail()[1]:
            from llm.orchestrator import handle_send_reminder
            result = await handle_send_reminder(reminder_params)
        assert result.success is True


class TestHandleFollowUp:
    @pytest.mark.asyncio
    async def test_returns_success(self, follow_up_params):
        with _mock_gmail()[0], _mock_gmail()[1]:
            from llm.orchestrator import handle_follow_up
            result = await handle_follow_up(follow_up_params)
        assert result.success is True


class TestHandleRequestDocuments:
    @pytest.mark.asyncio
    async def test_returns_success(self, request_documents_params):
        with _mock_gmail()[0], _mock_gmail()[1]:
            from llm.orchestrator import handle_request_documents
            result = await handle_request_documents(request_documents_params)
        assert result.success is True
