"""email_sender/sender.py — Send emails via SMTP. Falls back to logging if not configured."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from server.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_CONFIGURED

log = logging.getLogger(__name__)


async def send_email(
    to: str,
    subject: str,
    body: str,
    attachment_bytes: bytes | None = None,
    attachment_filename: str | None = None,
) -> bool:
    """Send an email via SMTP. Returns True on success.

    If SMTP is not configured, logs the email and returns False.
    """
    if not SMTP_CONFIGURED:
        log.warning("SMTP not configured — email logged only")
        _log_email(to, subject, body, attachment_filename)
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if attachment_bytes and attachment_filename:
            att = MIMEApplication(attachment_bytes, Name=attachment_filename)
            att["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
            msg.attach(att)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        log.info(f"Email sent to {to}: {subject}")
        return True

    except Exception as exc:
        log.error(f"SMTP send failed: {exc}", exc_info=True)
        _log_email(to, subject, body, attachment_filename)
        return False


def _log_email(to: str, subject: str, body: str, filename: str | None = None) -> None:
    """Print email to console as fallback."""
    print("\n" + "=" * 60)
    print("  EMAIL (not sent — SMTP not configured)")
    print("=" * 60)
    print(f"  To:      {to}")
    print(f"  Subject: {subject}")
    if filename:
        print(f"  Attach:  {filename}")
    print("-" * 60)
    print(body[:500])
    print("=" * 60 + "\n")
