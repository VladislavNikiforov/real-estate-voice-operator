"""telegram/bot.py — Telegram notification bot.

Sends notifications to the operator after pipeline tasks complete.
Usage: call send_notification() from the orchestrator after a task finishes.
"""

import logging
import os

import httpx

log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

_BASE_URL = ""


def _api_url() -> str:
    global _BASE_URL
    if not _BASE_URL:
        token = TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
        _BASE_URL = f"https://api.telegram.org/bot{token}"
    return _BASE_URL


async def send_notification(
    message: str,
    chat_id: str | None = None,
) -> bool:
    """Send a Telegram message to the operator.

    Args:
        message: Text to send (supports HTML formatting).
        chat_id: Override chat ID. Falls back to TELEGRAM_CHAT_ID env var.

    Returns:
        True if sent successfully, False otherwise.
    """
    target = chat_id or TELEGRAM_CHAT_ID or os.getenv("TELEGRAM_CHAT_ID", "")
    if not target:
        log.warning("TELEGRAM_CHAT_ID not set — skipping notification")
        return False

    token = TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        log.warning("TELEGRAM_BOT_TOKEN not set — skipping notification")
        return False

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": target,
            "text": message,
            "parse_mode": "HTML",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            log.info(f"Telegram notification sent to {target}")
            return True
    except Exception as exc:
        log.error(f"Telegram notification failed: {exc}")
        return False


async def notify_task_complete(
    action: str,
    client_name: str,
    client_email: str,
    invoice_number: str | None = None,
    drive_link: str | None = None,
    amount: float | None = None,
    success: bool = True,
    chat_id: str | None = None,
) -> bool:
    """Send a formatted task completion notification."""
    if success:
        lines = ["<b>Task completed</b>"]
        lines.append(f"Action: {action}")
        lines.append(f"To: {client_name} ({client_email})")
        if invoice_number:
            lines.append(f"Invoice: {invoice_number}")
        if amount:
            lines.append(f"Amount: EUR {amount:,.2f}")
        if drive_link and drive_link.startswith("http"):
            lines.append(f'<a href="{drive_link}">View invoice in Drive</a>')
        msg = "\n".join(lines)
    else:
        msg = f"<b>Task failed</b>\nAction: {action}\nTo: {client_name}"

    return await send_notification(msg, chat_id)
