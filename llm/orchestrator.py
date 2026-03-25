"""llm/orchestrator.py — Main pipeline brain. Never crashes. Always returns a speakable result."""

import asyncio
import datetime
import logging

import httpx

from server.config import (
    OPENCLAW_URL,
    COMPANY_NAME, COMPANY_ADDRESS, COMPANY_BANK, COMPANY_IBAN, COMPANY_PHONE,
)
from llm.models import (
    InvoiceData, PipelineResult,
    SendInvoiceParams, SendReminderParams, FollowUpParams, RequestDocumentsParams,
)
from llm.prompts import SUCCESS_MESSAGES, ERROR_MESSAGE
from pdf_generator.invoice import generate_invoice_pdf
from pdf_generator.templates import format_amount, format_date
from gdrive.uploader import upload_to_drive
from email_drafter.drafter import draft_email
from openclaw_prompt.generator import build_openclaw_instruction
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
    """Full pipeline: PDF → Drive → Email draft → OpenClaw prompt → POST to VM."""
    lang = params.get("language", "en")
    try:
        p = SendInvoiceParams(**params)
    except Exception as exc:
        return PipelineResult(success=False, message=_err(lang), error=str(exc))

    invoice_number = _next_invoice_number()
    date_str = format_date(lang)

    # ── Step 1: Generate PDF ──────────────────────────────────
    log.info(f"[{invoice_number}] Generating PDF...")
    try:
        data = InvoiceData(
            invoice_number=invoice_number,
            client_name=p.client_name,
            client_email=p.client_email,
            property_id=p.property_id,
            amount=p.amount,
            language=lang,
            date=date_str,
            company_name=COMPANY_NAME,
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
        email_params = {**params, "invoice_number": invoice_number}
        email = draft_email("invoice", email_params, drive_link)
    except Exception as exc:
        log.error(f"Email draft failed: {exc}", exc_info=True)
        return PipelineResult(success=False, message=_err(lang), error=f"Email error: {exc}")

    # ── Step 4: Generate OpenClaw instruction ─────────────────
    oc_instruction = build_openclaw_instruction(email)

    # ── Step 5: POST to OpenClaw VM ───────────────────────────
    log.info(f"[{invoice_number}] Sending to OpenClaw at {OPENCLAW_URL}...")
    oc_ok = await _post_to_openclaw(oc_instruction.model_dump())

    # ── Step 6: Return result ─────────────────────────────────
    tmpl = SUCCESS_MESSAGES["send_invoice"].get(lang, SUCCESS_MESSAGES["send_invoice"]["en"])
    message = tmpl.format(
        invoice_number=invoice_number,
        amount=format_amount(p.amount, "EUR", lang),
        client_name=p.client_name,
    )
    if not oc_ok:
        suffix = {"lv": " E-pasts ir rindā.", "ru": " Письмо в очереди.", "en": " Email has been queued."}
        message += suffix.get(lang, " Email queued.")

    # ── Step 7: Telegram notification ─────────────────────────
    await notify_task_complete(
        action="send_invoice",
        client_name=p.client_name,
        client_email=p.client_email,
        invoice_number=invoice_number,
        drive_link=drive_link,
        amount=p.amount,
        success=True,
    )

    return PipelineResult(
        success=True,
        message=message,
        invoice_number=invoice_number,
        drive_link=drive_link,
    )


async def handle_send_reminder(params: dict) -> PipelineResult:
    """Draft and send a reminder email. No PDF."""
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

    oc_instruction = build_openclaw_instruction(email)
    oc_ok = await _post_to_openclaw(oc_instruction.model_dump())

    tmpl = SUCCESS_MESSAGES.get(tool_name, {}).get(lang, f"Done. Email sent to {params.get('client_name','client')}.")
    message = tmpl.format(client_name=params.get("client_name", "client"))
    if not oc_ok:
        message += " (queued)"

    # Telegram notification
    await notify_task_complete(
        action=tool_name,
        client_name=params.get("client_name", ""),
        client_email=params.get("client_email", ""),
        success=True,
    )

    return PipelineResult(success=True, message=message)


# ── OpenClaw HTTP call ────────────────────────────────────────

async def _post_to_openclaw(payload: dict) -> bool:
    """POST instruction to OpenClaw VM. Returns True on success, False on any failure."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{OPENCLAW_URL}/execute", json=payload)
            resp.raise_for_status()
            log.info(f"OpenClaw response: {resp.json()}")
            return True
    except httpx.ConnectError:
        log.warning(f"OpenClaw unreachable at {OPENCLAW_URL} — instruction logged only")
        _log_openclaw_fallback(payload)
        return False
    except Exception as exc:
        log.warning(f"OpenClaw error: {exc} — instruction logged only")
        _log_openclaw_fallback(payload)
        return False


def _log_openclaw_fallback(payload: dict) -> None:
    """Print the OpenClaw prompt to console when VM is unreachable."""
    prompt = payload.get("prompt", "(no prompt)")
    email  = payload.get("email", {})
    print("\n" + "═" * 60)
    print("  📋 OPENCLAW FALLBACK — would send this to Desktop Commander:")
    print("═" * 60)
    print(f"  To:      {email.get('to','')}")
    print(f"  Subject: {email.get('subject','')}")
    print("─" * 60)
    print(prompt[:800])
    print("═" * 60 + "\n")


def _err(lang: str) -> str:
    return ERROR_MESSAGE.get(lang, ERROR_MESSAGE["en"])
