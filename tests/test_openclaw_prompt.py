"""Tests for OpenClaw prompt generation."""
import pytest
from llm.models import EmailDraft
from openclaw_prompt.generator import generate_gmail_prompt, build_openclaw_instruction


class TestGenerateGmailPrompt:
    def _email(self, drive_link=None):
        return EmailDraft(
            to="test@example.com",
            subject="Invoice INV-2026-1001",
            body="Dear John,\n\nPlease find your invoice.",
            drive_link=drive_link,
            language="en",
        )

    def test_prompt_contains_recipient(self):
        prompt = generate_gmail_prompt(self._email())
        assert "test@example.com" in prompt

    def test_prompt_contains_subject(self):
        prompt = generate_gmail_prompt(self._email())
        assert "INV-2026-1001" in prompt

    def test_prompt_contains_body(self):
        prompt = generate_gmail_prompt(self._email())
        assert "Dear John" in prompt

    def test_prompt_with_drive_link_mentions_link(self):
        link = "https://drive.google.com/file/d/abc/view"
        prompt = generate_gmail_prompt(self._email(drive_link=link))
        assert "Drive" in prompt or "link" in prompt.lower()

    def test_prompt_without_link_no_attach_instructions(self):
        prompt = generate_gmail_prompt(self._email(drive_link=None))
        assert "Compose" in prompt or "compose" in prompt

    def test_build_instruction_has_correct_action(self):
        instr = build_openclaw_instruction(self._email())
        assert instr.action == "send_email_gmail"
        assert instr.email.to == "test@example.com"
        assert len(instr.prompt) > 50
