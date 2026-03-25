"""Tests for PDF invoice generation."""
import datetime
import pytest
from llm.models import InvoiceData
from pdf_generator.invoice import generate_invoice_pdf
from pdf_generator.templates import format_amount, format_date


class TestFormatAmount:
    def test_latvian_format(self):
        result = format_amount(85000, "EUR", "lv")
        assert "85" in result and "EUR" in result

    def test_english_format(self):
        result = format_amount(85000, "EUR", "en")
        assert result == "€85,000.00"

    def test_russian_format(self):
        result = format_amount(100000, "EUR", "ru")
        assert "EUR" in result


class TestGenerateInvoicePdf:
    def _make_data(self, language="en") -> InvoiceData:
        return InvoiceData(
            invoice_number="INV-2026-1001",
            client_name="John Smith",
            client_email="john@example.com",
            property_id="apt-3",
            amount=85000,
            language=language,
            date=format_date(language),
            company_name="Test SIA",
            company_address="Test St 1, Riga",
            company_bank="Swedbank",
            company_iban="LV00HABA0000000000000",
            company_phone="+371 20000000",
        )

    def test_returns_bytes(self):
        pdf = generate_invoice_pdf(self._make_data())
        assert isinstance(pdf, bytes)
        assert len(pdf) > 1000

    def test_starts_with_pdf_header(self):
        pdf = generate_invoice_pdf(self._make_data())
        assert pdf[:4] == b"%PDF"

    def test_latvian_invoice(self):
        data = self._make_data("lv")
        data = data.model_copy(update={"client_name": "Jānis Bērziņš"})
        pdf = generate_invoice_pdf(data)
        assert pdf[:4] == b"%PDF"

    def test_russian_invoice(self):
        data = self._make_data("ru")
        data = data.model_copy(update={"client_name": "Ivan Petrov"})
        pdf = generate_invoice_pdf(data)
        assert pdf[:4] == b"%PDF"

    def test_all_languages(self):
        for lang in ("lv", "ru", "en"):
            pdf = generate_invoice_pdf(self._make_data(lang))
            assert pdf[:4] == b"%PDF", f"PDF generation failed for language: {lang}"
