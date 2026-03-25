# openclaw/gmail_flow.py
# ============================================================
# 🖥️ OWNER: @openclaw-person
# PURPOSE: Define/verify the Gmail automation flow for Desktop Commander.
#
# The prompt we generate tells Desktop Commander to:
#   1. Open gmail.com in the browser
#   2. Click "Compose"
#   3. Fill "To" field
#   4. Fill "Subject" field
#   5. Paste body (includes the Google Drive link)
#   6. Click "Send"
#
# This file can contain:
# - Step verification helpers (did Gmail open? did Compose appear?)
# - Screenshot capture for debugging
# - Retry logic for flaky steps
# - Flow constants (CSS selectors, timeouts)
#
# TODO(@openclaw-person): Implement verification and retry helpers
# ============================================================

# Gmail UI selectors — update if Gmail changes its layout
GMAIL_URL        = "https://mail.google.com"
COMPOSE_SELECTOR = "[gh='cm']"        # Compose button
TO_SELECTOR      = "input[name='to']"
SUBJECT_SELECTOR = "input[name='subjectbox']"
BODY_SELECTOR    = "div[aria-label='Message Body']"
SEND_SELECTOR    = "div[aria-label*='Send']"

# Timeouts
COMPOSE_TIMEOUT  = 10   # seconds to wait for compose window
SEND_TIMEOUT     = 15   # seconds to wait for "Message sent" indicator


def build_verification_steps(to: str, subject: str) -> list[str]:
    """
    Return a list of verification steps to check after sending.
    Pass these to Desktop Commander as post-send verification.

    TODO(@openclaw-person): Implement based on how Desktop Commander
    reports back verification results.
    """
    return [
        f"Verify 'Message sent' notification appeared",
        f"Check Sent folder contains email to {to} with subject '{subject[:30]}'",
    ]
