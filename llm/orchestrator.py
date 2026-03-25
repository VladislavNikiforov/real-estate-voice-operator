"""llm/orchestrator.py — Main pipeline brain. Never crashes. Always returns a speakable result.

Email sending flow:
  1. Generate PDF → save to generated_files/
  2. Draft email subject + body
  3. Send via sendmail_skill (Node.js Puppeteer → Chrome port 9222 → Gmail)
"""

import asyncio
import datetime
import logging
import os
import subprocess
from pathlib import Path

from dashboard.events import emit_step_start, emit_step_done, emit_invoice, emit_email_sent
from server.config import (
    COMPANY_NAME, COMPANY_REG_NR, COMPANY_VAT_NR,
    COMPANY_ADDRESS, COMPANY_BANK, COMPANY_IBAN, COMPANY_PHONE,
    CHROME_DEBUG_PORT,
)
from llm.models import (
    InvoiceData, LineItem, PipelineResult,
    SendInvoiceParams, SendReminderParams, FollowUpParams, RequestDocumentsParams,
)
from notion.client import lookup_client, lookup_service
from llm.prompts import SUCCESS_MESSAGES, ERROR_MESSAGE
from pdf_generator.invoice import generate_invoice_pdf
from pdf_generator.templates import format_amount, format_date
from email_drafter.drafter import draft_email

log = logging.getLogger(__name__)

# Directory where PDFs are saved locally
_GENERATED_DIR = Path(__file__).parent.parent / "generated_files"
_GENERATED_DIR.mkdir(exist_ok=True)

# Path to the sendmail_skill script
_SENDMAIL_SCRIPT = Path(__file__).parent.parent / "scripts" / "sendmail_skill" / "send-gmail.js"

# ── Invoice counter (in-memory for hackathon) ─────────────────
_invoice_counter = 1000


def _next_invoice_number() -> str:
    global _invoice_counter
    _invoice_counter += 1
    year = datetime.datetime.utcnow().year
    return f"INV-{year}-{_invoice_counter:04d}"


# ── sendmail_skill caller ─────────────────────────────────────

async def _send_via_sendmail_skill(
    to: str,
    subject: str,
    body: str,
    pdf_path: str | None = None,
) -> bool:
    """Call the Node.js sendmail_skill script to send email via Chrome/Gmail.

    Requires Chrome running with --remote-debugging-port=CHROME_DEBUG_PORT.
    Returns True on success.
    """
    if not _SENDMAIL_SCRIPT.exists():
        log.error(f"sendmail_skill not found at {_SENDMAIL_SCRIPT}")
        return False

    cmd = [
        "node", str(_SENDMAIL_SCRIPT),
        "--to", to,
        "--subject", subject,
        "--body", body,
    ]
    if pdf_path and Path(pdf_path).exists():
        cmd += ["--file", pdf_path]
    if CHROME_DEBUG_PORT != 9222:
        cmd += ["--port", str(CHROME_DEBUG_PORT)]

    log.info(f"sendmail_skill: sending to {to} | subject: {subject}")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
        out = stdout.decode().strip()
        err = stderr.decode().strip()

        log.info(f"sendmail_skill stdout: {out}")
        if err:
            log.warning(f"sendmail_skill stderr: {err}")

        if proc.returncode == 0 and "SUCCESS" in out:
            log.info(f"Email sent successfully to {to}")
            return True
        else:
            log.error(f"sendmail_skill failed (exit {proc.returncode}): {err or out}")
            return False

    except asyncio.TimeoutError:
        log.error("sendmail_skill timed out after 90s")
        return False
    except FileNotFoundError:
        log.error("node not found — is Node.js installed?")
        return False
    except Exception as exc:
        log.error(f"sendmail_skill error: {exc}", exc_info=True)
        return False


# ── Public handlers ───────────────────────────────────────────

async def handle_send_invoice(params: dict) -> PipelineResult:
    """Full pipeline: Notion lookup → PDF → save locally → sendmail_skill."""
    lang = params.get("language", "lv")
    try:
        p = SendInvoiceParams(**params)
    except Exception as exc:
        return PipelineResult(success=False, message=_err(lang), error=str(exc))

    # ── Step 0: Notion lookup (best-effort) ───────────────────
    client_data = None
    service_data = None

    try:
        from notion.client import lookup_client, lookup_service
        client_data = await lookup_client(p.client_name)
        if p.service_name:
            service_data = await lookup_service(p.service_name)
    except Exception as exc:
        log.warning(f"Notion lookup skipped: {exc}")

    # Resolve email
    client_email = p.client_email or (client_data or {}).get("E-pasts", "")
    if not client_email:
        return PipelineResult(
            success=False, message=_err(lang),
            error=f"No email found for '{p.client_name}'",
        )

    # Resolve amounts
    unit_price = p.amount
    vat_rate = 0.0
    unit = ""
    service_desc = p.service_name or p.property_id or "Service"

    if service_data:
        unit_price = service_data.get("Likme (EUR)", 0) or p.amount
        vat_rate   = service_data.get("PVN likme (%)", 0) or 0.0
        unit       = service_data.get("Mērvienība", "")
        service_desc = service_data.get("Pakalpojums", service_desc)

    subtotal   = round(p.quantity * unit_price, 2)
    vat_amount = round(subtotal * vat_rate, 2)
    total      = round(subtotal + vat_amount, 2)

    line_items = [LineItem(
        description=service_desc,
        quantity=p.quantity,
        unit=unit,
        unit_price=unit_price,
        amount=subtotal,
    )]

    invoice_number = _next_invoice_number()
    date_str = format_date(lang)

    # ── Step 1: Generate PDF ──────────────────────────────────
    emit_step_start("pdf", "Generate PDF", f"{invoice_number}")
    log.info(f"[{invoice_number}] Generating PDF...")
    try:
        data = InvoiceData(
            invoice_number=invoice_number,
            client_name=client_data.get("Nosaukums", p.client_name) if client_data else p.client_name,
            client_email=client_email,
            client_reg_nr=client_data.get("Reģ. nr.", "") if client_data else "",
            client_vat_nr=client_data.get("PVN nr.", "") if client_data else "",
            client_address=client_data.get("Adrese", "") if client_data else "",
            client_bank=client_data.get("Banka", "") if client_data else "",
            client_iban=client_data.get("IBAN", "") if client_data else "",
            payment_terms=client_data.get("Apmaksas termiņš", "") if client_data else "",
            line_items=line_items,
            subtotal=subtotal,
            vat_rate=vat_rate,
            vat_amount=vat_amount,
            total=total,
            amount=total,
            property_id=p.property_id,
            language=lang,
            date=date_str,
            company_name=COMPANY_NAME,
            company_reg_nr=COMPANY_REG_NR,
            company_vat_nr=COMPANY_VAT_NR,
            company_address=COMPANY_ADDRESS,
            company_bank=COMPANY_BANK,
            company_iban=COMPANY_IBAN,
            company_phone=COMPANY_PHONE,
            notes=p.notes,
        )
        pdf_bytes = generate_invoice_pdf(data)
        log.info(f"[{invoice_number}] PDF generated ({len(pdf_bytes):,} bytes)")
        emit_step_done("pdf", "Generate PDF", f"{len(pdf_bytes):,} bytes")
    except Exception as exc:
        log.error(f"PDF generation failed: {exc}", exc_info=True)
        return PipelineResult(success=False, message=_err(lang), error=f"PDF error: {exc}")

    # ── Step 2: Save PDF locally ──────────────────────────────
    pdf_filename = f"invoice_{invoice_number}.pdf"
    pdf_path = str(_GENERATED_DIR / pdf_filename)
    try:
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        log.info(f"[{invoice_number}] PDF saved: {pdf_path}")
    except Exception as exc:
        log.error(f"PDF save failed: {exc}")
        pdf_path = None

    # ── Step 3: Draft email ───────────────────────────────────
    emit_step_start("email_draft", "Draft Email", client_email)
    log.info(f"[{invoice_number}] Drafting email...")
    try:
        email_params = {**params, "client_email": client_email, "amount": total, "invoice_number": invoice_number}
        email = draft_email("invoice", email_params)
    except Exception as exc:
        log.error(f"Email draft failed: {exc}", exc_info=True)
        return PipelineResult(success=False, message=_err(lang), error=f"Email error: {exc}")

    emit_step_done("email_draft", "Draft Email", email.subject)

    # ── Step 4: Send via sendmail_skill ───────────────────────
    emit_step_start("email_send", "Send Email", client_email)
    log.info(f"[{invoice_number}] Sending email to {client_email} via sendmail_skill...")
    sent = await _send_via_sendmail_skill(
        to=client_email,
        subject=email.subject,
        body=email.body,
        pdf_path=pdf_path,
    )

    emit_step_done("email_send", "Send Email", "sent" if sent else "failed")
    emit_email_sent(client_email, email.subject, sent)
    emit_invoice(invoice_number, format_amount(total, "EUR", lang), data.client_name)

    # ── Step 5: Build result ──────────────────────────────────
    tmpl = SUCCESS_MESSAGES["send_invoice"].get(lang, SUCCESS_MESSAGES["send_invoice"]["en"])
    message = tmpl.format(
        invoice_number=invoice_number,
        amount=format_amount(total, "EUR", lang),
        client_name=data.client_name,
    )
    if not sent:
        suffix = {"lv": " E-pasts nav nosūtīts.", "ru": " Письмо не отправлено.", "en": " Email could not be sent — check Chrome is open."}
        message += suffix.get(lang, suffix["en"])

    return PipelineResult(
        success=sent,
        message=message,
        invoice_number=invoice_number,
        drive_link=None,
    )


async def handle_send_reminder(params: dict) -> PipelineResult:
    lang = params.get("language", "en")
    try:
        SendReminderParams(**params)
    except Exception as exc:
        return PipelineResult(success=False, message=_err(lang), error=str(exc))
    return await _simple_pipeline("reminder", "send_reminder", params, lang)


async def handle_follow_up(params: dict) -> PipelineResult:
    lang = params.get("language", "en")
    try:
        FollowUpParams(**params)
    except Exception as exc:
        return PipelineResult(success=False, message=_err(lang), error=str(exc))
    return await _simple_pipeline("follow_up", "follow_up", params, lang)


async def handle_request_documents(params: dict) -> PipelineResult:
    lang = params.get("language", "en")
    try:
        RequestDocumentsParams(**params)
    except Exception as exc:
        return PipelineResult(success=False, message=_err(lang), error=str(exc))
    return await _simple_pipeline("request_documents", "request_documents", params, lang)


# ── Simple pipeline (no PDF) ──────────────────────────────────

async def _simple_pipeline(email_action: str, tool_name: str, params: dict, lang: str) -> PipelineResult:
    try:
        email = draft_email(email_action, params)
    except Exception as exc:
        log.error(f"Email draft failed: {exc}", exc_info=True)
        return PipelineResult(success=False, message=_err(lang), error=str(exc))

    sent = await _send_via_sendmail_skill(
        to=email.to,
        subject=email.subject,
        body=email.body,
    )

    tmpl = SUCCESS_MESSAGES.get(tool_name, {}).get(lang, f"Done. Email sent to {params.get('client_name','client')}.")
    message = tmpl.format(client_name=params.get("client_name", "client"))
    if not sent:
        message += " (email sending failed)"

    return PipelineResult(success=sent, message=message)


def _err(lang: str) -> str:
    return ERROR_MESSAGE.get(lang, ERROR_MESSAGE["en"])
