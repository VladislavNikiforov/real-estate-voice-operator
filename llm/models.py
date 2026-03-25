"""llm/models.py — Pydantic models for all data flowing through the pipeline."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class InvoiceData(BaseModel):
    invoice_number: str
    client_name: str
    client_email: str
    property_id: str
    amount: float
    currency: str = "EUR"
    language: str
    date: str                    # "25.03.2026"
    company_name: str
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
    client_email: str
    property_id: str
    amount: float
    language: str
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
