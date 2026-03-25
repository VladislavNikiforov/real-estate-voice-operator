"""llm/models.py — Pydantic models for all data flowing through the pipeline."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class LineItem(BaseModel):
    description: str
    quantity: float
    unit: str = ""               # "stunda", "gab.", etc.
    unit_price: float
    amount: float                # quantity * unit_price


class InvoiceData(BaseModel):
    invoice_number: str
    client_name: str
    client_email: str
    client_reg_nr: str = ""
    client_vat_nr: str = ""
    client_address: str = ""
    client_bank: str = ""
    client_iban: str = ""
    payment_terms: str = ""      # "30 dienas"
    line_items: list[LineItem] = []
    subtotal: float = 0.0
    vat_rate: float = 0.0        # e.g. 0.21
    vat_amount: float = 0.0
    total: float = 0.0
    # Legacy fields (kept for backward compat with simple flow)
    property_id: str = ""
    amount: float = 0.0
    currency: str = "EUR"
    language: str
    date: str                    # "25.03.2026"
    company_name: str
    company_reg_nr: str = ""
    company_vat_nr: str = ""
    company_address: str
    company_bank: str
    company_iban: str
    company_phone: str = ""
    notes: Optional[str] = None

    @field_validator("language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        return v if v in ("lv", "ru", "en") else "en"


class EmailDraft(BaseModel):
    to: str
    subject: str
    body: str
    drive_link: Optional[str] = None
    language: str = "en"


class OpenClawInstruction(BaseModel):
    action: str = "send_email_gmail"
    email: EmailDraft
    prompt: str                  # Natural language prompt for Desktop Commander


class PipelineResult(BaseModel):
    success: bool
    message: str                 # Vapi speaks this back to the caller
    invoice_number: Optional[str] = None
    drive_link: Optional[str] = None
    error: Optional[str] = None


# ── Tool call parameter models ────────────────────────────────

class SendInvoiceParams(BaseModel):
    client_name: str
    client_email: str = ""       # optional — looked up from Notion if empty
    service_name: str = ""       # looked up in Services DB for rate
    quantity: float = 1.0
    amount: float = 0.0          # optional — calculated from service if 0
    property_id: str = ""        # legacy, optional
    language: str = "lv"
    notes: Optional[str] = None


class SendReminderParams(BaseModel):
    client_name: str
    client_email: str
    language: str
    property_id: Optional[str] = None
    amount: Optional[float] = None


class FollowUpParams(BaseModel):
    client_name: str
    client_email: str
    language: str
    property_id: Optional[str] = None
    notes: Optional[str] = None


class RequestDocumentsParams(BaseModel):
    client_name: str
    client_email: str
    documents_needed: str
    language: str
