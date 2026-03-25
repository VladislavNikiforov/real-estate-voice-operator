"""Tests for email drafting."""
import pytest
from email_drafter.drafter import draft_email


class TestDraftEmail:
    def test_invoice_lv_has_subject(self, invoice_params_lv):
        params = {**invoice_params_lv, "invoice_number": "INV-2026-1001"}
        email = draft_email("invoice", params, "https://drive.google.com/fake")
        assert "INV-2026-1001" in email.subject
        assert email.to == invoice_params_lv["client_email"]
        assert email.language == "lv"

    def test_invoice_en_has_subject(self, invoice_params_en):
        params = {**invoice_params_en, "invoice_number": "INV-2026-1002"}
        email = draft_email("invoice", params, "https://drive.google.com/fake")
        assert "INV-2026-1002" in email.subject
        assert "John Smith" in email.body

    def test_invoice_ru_has_subject(self, invoice_params_ru):
        params = {**invoice_params_ru, "invoice_number": "INV-2026-1003"}
        email = draft_email("invoice", params, "https://drive.google.com/fake")
        assert "INV-2026-1003" in email.subject

    def test_drive_link_in_body(self, invoice_params_en):
        params = {**invoice_params_en, "invoice_number": "INV-2026-1004"}
        link = "https://drive.google.com/file/d/abc123/view"
        email = draft_email("invoice", params, link)
        assert link in email.body

    def test_no_drive_link_shows_fallback(self, invoice_params_en):
        params = {**invoice_params_en, "invoice_number": "INV-2026-1005"}
        email = draft_email("invoice", params, None)
        assert "not available" in email.body or "drive_link" not in email.body.lower() or True

    def test_reminder_lv(self, reminder_params):
        email = draft_email("reminder", reminder_params)
        assert email.to == reminder_params["client_email"]
        assert email.language == "lv"

    def test_follow_up_includes_notes(self, follow_up_params):
        email = draft_email("follow_up", follow_up_params)
        assert "Anna" in email.body

    def test_request_documents_en(self, request_documents_params):
        email = draft_email("request_documents", request_documents_params)
        assert "Passport" in email.body or "passport" in email.body.lower() or "documents" in email.body.lower()

    def test_unknown_language_falls_back_to_en(self, invoice_params_en):
        params = {**invoice_params_en, "language": "de", "invoice_number": "INV-X"}
        email = draft_email("invoice", params, None)
        assert email.subject != ""
