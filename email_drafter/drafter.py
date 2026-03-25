"""email_drafter/drafter.py — Compose email subject + body from templates."""

from pathlib import Path
from server.config import (
    COMPANY_NAME, COMPANY_BANK, COMPANY_IBAN, COMPANY_PHONE
)
from llm.models import EmailDraft
from pdf_generator.templates import format_amount

_TMPL_DIR = Path(__file__).parent / "templates"

# Map action → template file prefix
_ACTION_MAP = {
    "invoice":           "invoice",
    "reminder":          "reminder",
    "follow_up":         "follow_up",
    "request_documents": "request_documents",
}


def draft_email(
    action: str,
    params: dict,
    drive_link: str | None = None,
) -> EmailDraft:
    """Compose email for a given action.

    Args:
        action:     "invoice" | "reminder" | "follow_up" | "request_documents"
        params:     Dict with client_name, client_email, language, property_id, amount, etc.
        drive_link: Google Drive link for the invoice PDF (if any).

    Returns:
        EmailDraft with to, subject, body, drive_link, language.
    """
    lang       = params.get("language", "en")
    prefix     = _ACTION_MAP.get(action, "invoice")
    template   = _load_template(prefix, lang)
    subject, body = _render(template, action, params, drive_link)

    return EmailDraft(
        to=params["client_email"],
        subject=subject,
        body=body,
        drive_link=drive_link,
        language=lang,
    )


# ── Internal helpers ──────────────────────────────────────────

def _load_template(prefix: str, lang: str) -> str:
    path = _TMPL_DIR / f"{prefix}_{lang}.txt"
    if not path.exists():
        path = _TMPL_DIR / f"{prefix}_en.txt"
    return path.read_text(encoding="utf-8")


def _render(template: str, action: str, params: dict, drive_link: str | None) -> tuple[str, str]:
    """Split template into subject/body and fill placeholders."""
    parts = template.split("---\n", 1)
    subject_line = parts[0].strip().removeprefix("subject:").strip()
    body_raw     = parts[1].strip() if len(parts) > 1 else template.strip()

    lang        = params.get("language", "en")
    amount      = params.get("amount")
    property_id = params.get("property_id", "")
    notes       = params.get("notes", "")

    formatted_amount = format_amount(amount, "EUR", lang) if amount else ""
    property_part    = f" — {property_id}" if property_id else ""
    amount_line      = f"Summa: {formatted_amount}\n\n" if formatted_amount else ""
    notes_line       = f"{notes}\n\n" if notes else ""

    vars_ = {
        "client_name":      params.get("client_name", ""),
        "client_email":     params.get("client_email", ""),
        "property_id":      property_id,
        "property_part":    property_part,
        "invoice_number":   params.get("invoice_number", ""),
        "formatted_amount": formatted_amount,
        "amount_line":      amount_line,
        "notes_line":       notes_line,
        "drive_link":       drive_link or "(document not available)",
        "documents_needed": params.get("documents_needed", ""),
        "company_name":     COMPANY_NAME,
        "company_bank":     COMPANY_BANK,
        "company_iban":     COMPANY_IBAN,
        "company_phone":    COMPANY_PHONE,
    }

    subject = subject_line.format_map(_SafeMap(vars_))
    body    = body_raw.format_map(_SafeMap(vars_))
    return subject, body


class _SafeMap(dict):
    """Return '{key}' for any missing key instead of raising KeyError."""
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
