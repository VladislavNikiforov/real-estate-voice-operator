"""llm/orchestrator.py — Main pipeline brain. Never crashes. Always returns a speakable result."""

import asyncio
import datetime
import logging

from server.config import (
    COMPANY_NAME, COMPANY_REG_NR, COMPANY_VAT_NR,
    COMPANY_ADDRESS, COMPANY_BANK, COMPANY_IBAN, COMPANY_PHONE,
)
from llm.models import (
    InvoiceData, LineItem, PipelineResult,
    SendInvoiceParams, SendReminderParams, FollowUpParams, RequestDocumentsParams,
)
from notion.client import lookup_client, lookup_service
from llm.prompts import SUCCESS_MESSAGES, ERROR_MESSAGE
from pdf_generator.invoice import generate_invoice_pdf
from pdf_generator.templates import format_amount, format_date
from gdrive.uploader import upload_to_drive
from email_drafter.drafter import draft_email
from gmail.sender import send_email
from telegram.bot import notify_task_complete

log = logging.getLogger(__name__)

# ── Invoice counter (in-memory for hackathon) ─────────────────
_invoice_counter = 1000


def _next_invoice_number() -> str:
    global _invoice_counter
    _invoice_counter += 1
    year = datetime.datetime.utcnow().year
    return f"INV-{year}-{_invoice_counter:04d}"


# ── Public handlers ───────────────────────────────────────────

async def handle_send_invoice(params: dict) -> PipelineResult:
    """Full pipeline: Notion lookup → PDF → Drive → Gmail API send → Telegram notify."""
    lang = params.get("language", "lv")
    try:
        p = SendInvoiceParams(**params)
    except Exception as exc:
        return PipelineResult(success=False, message=_err(lang), error=str(exc))

    # ── Step 0: Look up client and service from Notion ────────
    client_data = None
    service_data = None

    try:
        client_data = await lookup_client(p.client_name)
    except Exception as exc:
        log.warning(f"Notion client lookup failed: {exc}")

    if p.service_name:
        try:
            service_data = await lookup_service(p.service_name)
        except Exception as exc:
            log.warning(f"Notion service lookup failed: {exc}")

    # Resolve client email: param > Notion > empty
    client_email = p.client_email or (client_data or {}).get("E-pasts", "")
    if not client_email:
        return PipelineResult(
            success=False, message=_err(lang),
            error=f"No email found for client '{p.client_name}'",
        )

    # Calculate amount from service rate x quantity, or use explicit amount
    vat_rate = 0.0
    unit = ""
    unit_price = p.amount
    line_items = []

    if service_data:
        unit_price = service_data.get("Likme (EUR)", 0) or p.amount
        vat_rate = service_data.get("PVN likme (%)", 0) or 0.0
        unit = service_data.get("Mērvienība", "")
        service_desc = service_data.get("Pakalpojums", p.service_name)
    else:
        service_desc = p.service_name or p.property_id or "Service"
        if p.amount:
            unit_price = p.amount

    subtotal = p.quantity * unit_price
    vat_amount = round(subtotal * vat_rate, 2)
    total = round(subtotal + vat_amount, 2)

    line_items.append(LineItem(
        description=service_desc,
        quantity=p.quantity,
        unit=unit,
        unit_price=unit_price,
        amount=subtotal,
    ))

    invoice_number = _next_invoice_number()
    date_str = format_date(lang)

    # ── Step 1: Generate PDF ──────────────────────────────────
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
    except Exception as exc:
        log.error(f"PDF generation failed: {exc}", exc_info=True)
        return PipelineResult(success=False, message=_err(lang), error=f"PDF error: {exc}")

    # ── Step 2: Upload to Drive ───────────────────────────────
    log.info(f"[{invoice_number}] Uploading to Drive...")
    try:
        filename = f"invoice_{invoice_number}.pdf"
        drive_link = await upload_to_drive(pdf_bytes, filename)
        log.info(f"[{invoice_number}] Drive link: {drive_link}")
    except Exception as exc:
        log.warning(f"Drive upload failed ({exc}), continuing without link")
        drive_link = None

    # ── Step 3: Draft email ───────────────────────────────────
    log.info(f"[{invoice_number}] Drafting email...")
    try:
        email_params = {
            **params,
            "client_email": client_email,
            "amount": total,
            "invoice_number": invoice_number,
        }
        email = draft_email("invoice", email_params, drive_link)
    except Exception as exc:
        log.error(f"Email draft failed: {exc}", exc_info=True)
        return PipelineResult(success=False, message=_err(lang), error=f"Email error: {exc}")

    # ── Step 4: Send via Gmail API ────────────────────────────
    log.info(f"[{invoice_number}] Sending email via Gmail API to {email.to}...")
    gmail_result = await send_email(
        to=email.to,
        subject=email.subject,
        body=email.body,
        pdf_bytes=pdf_bytes,
        pdf_filename=filename,
    )

    # ── Step 5: Build result message ──────────────────────────
    tmpl = SUCCESS_MESSAGES["send_invoice"].get(lang, SUCCESS_MESSAGES["send_invoice"]["en"])
    message = tmpl.format(
        invoice_number=invoice_number,
        amount=format_amount(total, "EUR", lang),
        client_name=data.client_name,
    )
    if not gmail_result.get("success"):
        suffix = {"lv": " E-pasts ir rindā.", "ru": " Письмо в очереди.", "en": " Email sending failed — check Gmail auth."}
        message += suffix.get(lang, suffix["en"])
        log.error(f"Gmail send failed: {gmail_result.get('error')}")

    # ── Step 6: Telegram notification ─────────────────────────
    await notify_task_complete(
        action="send_invoice",
        client_name=p.client_name,
        client_email=client_email,
        invoice_number=invoice_number,
        drive_link=drive_link,
        amount=total,
        success=gmail_result.get("success", False),
    )

    return PipelineResult(
        success=gmail_result.get("success", False),
        message=message,
        invoice_number=invoice_number,
        drive_link=drive_link,
    )


async def handle_send_reminder(params: dict) -> PipelineResult:
    """Draft and send a reminder email via Gmail. No PDF."""
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


# ── Shared simple pipeline (no PDF) ──────────────────────────

async def _simple_pipeline(
    email_action: str,
    tool_name: str,
    params: dict,
    lang: str,
) -> PipelineResult:
    try:
        email = draft_email(email_action, params)
    except Exception as exc:
        log.error(f"Email draft failed: {exc}", exc_info=True)
        return PipelineResult(success=False, message=_err(lang), error=str(exc))

    # Send via Gmail API
    gmail_result = await send_email(
        to=email.to,
        subject=email.subject,
        body=email.body,
    )

    tmpl = SUCCESS_MESSAGES.get(tool_name, {}).get(lang, f"Done. Email sent to {params.get('client_name','client')}.")
    message = tmpl.format(client_name=params.get("client_name", "client"))
    if not gmail_result.get("success"):
        message += f" (Gmail error: {gmail_result.get('error', 'unknown')})"

    # Telegram notification
    await notify_task_complete(
        action=tool_name,
        client_name=params.get("client_name", ""),
        client_email=params.get("client_email", ""),
        success=gmail_result.get("success", False),
    )

    return PipelineResult(success=gmail_result.get("success", False), message=message)


def _err(lang: str) -> str:
    return ERROR_MESSAGE.get(lang, ERROR_MESSAGE["en"])
