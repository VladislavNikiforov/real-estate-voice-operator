"""openclaw_prompt/templates.py — Prompt templates for Desktop Commander."""

GMAIL_SEND_TEMPLATE = """\
Open Gmail in the browser and compose a new email.

RECIPIENT: {to}
SUBJECT: {subject}

EMAIL BODY:
{body}

STEPS:
1. Click the "Compose" button in Gmail
2. In the "To" field, enter: {to}
3. In the "Subject" field, enter: {subject}
4. In the message body, paste the email body above
5. Click "Send"

IMPORTANT:
- Make sure the email is sent, not just saved as draft
- If Gmail asks for confirmation, confirm and send
- Report back whether the email was sent successfully
"""

GMAIL_SEND_WITH_LINK_TEMPLATE = """\
Open Gmail in the browser and compose a new email.

RECIPIENT: {to}
SUBJECT: {subject}

EMAIL BODY:
{body}

The email body contains a Google Drive link to the invoice document.
Do NOT try to download or attach the file — the link in the body is sufficient.

STEPS:
1. Click the "Compose" button in Gmail
2. In the "To" field, enter: {to}
3. In the "Subject" field, enter: {subject}
4. In the message body, paste the email body above exactly as written
5. Click "Send"

Report whether the email was sent successfully.
"""
