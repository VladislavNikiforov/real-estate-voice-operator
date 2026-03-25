"""openclaw_prompt/generator.py — Generate Desktop Commander instruction prompts."""

from llm.models import EmailDraft, OpenClawInstruction
from openclaw_prompt.templates import GMAIL_SEND_TEMPLATE, GMAIL_SEND_WITH_LINK_TEMPLATE


def generate_gmail_prompt(email: EmailDraft) -> str:
    """Build the natural-language instruction for OpenClaw + Desktop Commander.

    If the email has a Drive link, uses the link-specific template which
    tells Desktop Commander NOT to try attaching a file.

    Returns the full prompt string.
    """
    template = GMAIL_SEND_WITH_LINK_TEMPLATE if email.drive_link else GMAIL_SEND_TEMPLATE
    return template.format(
        to=email.to,
        subject=email.subject,
        body=email.body,
    )


def build_openclaw_instruction(email: EmailDraft) -> OpenClawInstruction:
    """Build a complete OpenClawInstruction ready to POST to the VM."""
    return OpenClawInstruction(
        action="send_email_gmail",
        email=email,
        prompt=generate_gmail_prompt(email),
    )
