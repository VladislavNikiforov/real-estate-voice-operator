"""gmail/sender.py — Send emails via Gmail API using OAuth2.

Requires:
- credentials/gmail_credentials.json (OAuth2 client from Google Cloud Console)
- credentials/gmail_token.json (auto-generated after first auth via scripts/gmail_setup.py)

Scopes: gmail.send, gmail.readonly
"""

import base64
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

_CREDS_DIR = Path(__file__).parent.parent / "credentials"
_CREDENTIALS_FILE = _CREDS_DIR / "gmail_credentials.json"
_TOKEN_FILE = _CREDS_DIR / "gmail_token.json"


def _get_gmail_service():
    """Build and return an authenticated Gmail API service."""
    creds = None

    if _TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _TOKEN_FILE.write_text(creds.to_json())
        else:
            raise RuntimeError(
                "Gmail not authenticated. Run: python scripts/gmail_setup.py"
            )

    return build("gmail", "v1", credentials=creds)


async def send_email(
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None,
    pdf_filename: Optional[str] = None,
) -> dict:
    """Send an email via Gmail API.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body (plain text, will also send as HTML).
        from_email: Sender address (defaults to authenticated user).
        pdf_bytes: Optional PDF attachment bytes.
        pdf_filename: Filename for the PDF attachment.

    Returns:
        {"success": True/False, "message_id": "...", "error": "..."}
    """
    try:
        service = _get_gmail_service()

        msg = MIMEMultipart("mixed")
        msg["to"] = to
        msg["subject"] = subject
        if from_email:
            msg["from"] = from_email

        html_body = body.replace("\n", "<br>\n")
        msg.attach(MIMEText(html_body, "html"))

        if pdf_bytes and pdf_filename:
            part = MIMEBase("application", "pdf")
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{pdf_filename}"',
            )
            msg.attach(part)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        log.info(f"Email sent to {to}, message_id={result.get('id')}")
        return {"success": True, "message_id": result.get("id")}

    except RuntimeError as exc:
        log.error(f"Gmail auth error: {exc}")
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        log.error(f"Gmail send failed: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}


async def search_emails_gmail(
    query: str,
    max_results: int = 5,
) -> list[dict]:
    """Search emails via Gmail API.

    Args:
        query: Gmail search query (e.g. "from:john subject:invoice").
        max_results: Max number of emails to return.

    Returns:
        List of dicts with from, subject, snippet, date.
    """
    try:
        service = _get_gmail_service()

        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = result.get("messages", [])
        if not messages:
            return []

        emails = []
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            emails.append({
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "snippet": msg.get("snippet", ""),
                "date": headers.get("Date", ""),
            })

        return emails

    except RuntimeError as exc:
        log.error(f"Gmail auth error: {exc}")
        return []
    except Exception as exc:
        log.error(f"Gmail search failed: {exc}", exc_info=True)
        return []
