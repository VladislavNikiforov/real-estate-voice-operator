"""server/config.py — Load env vars, validate required, expose typed config."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _warn_if_missing(key: str, hint: str = "") -> None:
    if not os.getenv(key):
        msg = f"[CONFIG] WARNING: {key} is not set"
        if hint:
            msg += f" — {hint}"
        print(msg)


# ── Validate on import ────────────────────────────────────────
_warn_if_missing("ANTHROPIC_API_KEY", "Claude brain disabled")
_warn_if_missing("NOTION_TOKEN", "Notion client lookup disabled")
_warn_if_missing("OPENCLAW_URL", "falling back to http://localhost:8888")

# ── Server ────────────────────────────────────────────────────
PORT      = int(_get("PORT", "8000"))
LOG_LEVEL = _get("LOG_LEVEL", "DEBUG")

# ── Claude API ────────────────────────────────────────────────
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = _get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# ── Notion ────────────────────────────────────────────────────
NOTION_TOKEN       = _get("NOTION_TOKEN", "")
NOTION_CLIENTS_DB  = _get("NOTION_CLIENTS_DB", "")
NOTION_SERVICES_DB = _get("NOTION_SERVICES_DB", "")

# ── ElevenLabs ────────────────────────────────────────────────
ELEVENLABS_WEBHOOK_SECRET = _get("ELEVENLABS_WEBHOOK_SECRET", "")
ELEVENLABS_AGENT_ID       = _get("ELEVENLABS_AGENT_ID", "")

# ── Company info ──────────────────────────────────────────────
COMPANY_NAME    = _get("COMPANY_NAME",    'SIA "TEIKUMS JT"')
COMPANY_REG_NR  = _get("COMPANY_REG_NR",  "40203653629")
COMPANY_VAT_NR  = _get("COMPANY_VAT_NR",  "LV40203653629")
COMPANY_ADDRESS = _get("COMPANY_ADDRESS", "Gustava Zemgala gatve 78-1, Rīga, LV-1039")
COMPANY_PHONE   = _get("COMPANY_PHONE",   "+371 20000000")
COMPANY_EMAIL   = _get("COMPANY_EMAIL",   "info@teikums.lv")
COMPANY_BANK    = _get("COMPANY_BANK",    "Swedbank")
COMPANY_IBAN    = _get("COMPANY_IBAN",    "LV00HABA0000000000000")

# ── Google Drive (optional) ───────────────────────────────────
GDRIVE_CREDENTIALS_PATH = _get("GDRIVE_CREDENTIALS_PATH", "")
GDRIVE_FOLDER_ID        = _get("GDRIVE_FOLDER_ID", "")
GDRIVE_CONFIGURED       = bool(GDRIVE_CREDENTIALS_PATH and GDRIVE_FOLDER_ID)

# ── SMTP (optional fallback) ──────────────────────────────────
SMTP_HOST     = _get("SMTP_HOST", "")
SMTP_PORT     = int(_get("SMTP_PORT", "587"))
SMTP_USER     = _get("SMTP_USER", "")
SMTP_PASSWORD = _get("SMTP_PASSWORD", "")
SMTP_FROM     = _get("SMTP_FROM", "") or COMPANY_EMAIL
SMTP_CONFIGURED = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)

# ── Gmail OAuth2 ──────────────────────────────────────────────
GMAIL_CREDENTIALS_PATH = _get("GMAIL_CREDENTIALS_PATH", "credentials/gmail_credentials.json")

# ── sendmail_skill (Chrome debug port) ───────────────────────
CHROME_DEBUG_PORT = int(_get("CHROME_DEBUG_PORT", "9222"))

# ── OpenClaw (legacy) ─────────────────────────────────────────
OPENCLAW_URL = _get("OPENCLAW_URL", "http://localhost:8888")
