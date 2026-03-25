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
_warn_if_missing("OPENCLAW_URL", "falling back to http://localhost:8888")
_warn_if_missing("GDRIVE_CREDENTIALS_PATH", "Google Drive upload will save files locally")
_warn_if_missing("GDRIVE_FOLDER_ID", "Google Drive upload will save files locally")
_warn_if_missing("COMPANY_NAME", "using default company name")
_warn_if_missing("NOTION_TOKEN", "Notion client/service lookup disabled")

# ── Exported config ───────────────────────────────────────────
PORT = int(_get("PORT", "8000"))
LOG_LEVEL = _get("LOG_LEVEL", "DEBUG")

OPENCLAW_URL = _get("OPENCLAW_URL", "http://localhost:8888")

GDRIVE_CREDENTIALS_PATH = _get("GDRIVE_CREDENTIALS_PATH", "")
GDRIVE_FOLDER_ID = _get("GDRIVE_FOLDER_ID", "")

# ── Notion (Company OS) ─────────────────────────────────────
NOTION_TOKEN      = _get("NOTION_TOKEN", "")
NOTION_CLIENTS_DB = _get("NOTION_CLIENTS_DB", "")
NOTION_SERVICES_DB = _get("NOTION_SERVICES_DB", "")

# ── Company info (seller on invoices) ────────────────────────
COMPANY_NAME    = _get("COMPANY_NAME",    'SIA "TEIKUMS JT"')
COMPANY_REG_NR  = _get("COMPANY_REG_NR",  "40203653629")
COMPANY_VAT_NR  = _get("COMPANY_VAT_NR",  "LV40203653629")
COMPANY_ADDRESS = _get("COMPANY_ADDRESS", "Gustava Zemgala gatve 78-1, Rīga, LV-1039")
COMPANY_PHONE   = _get("COMPANY_PHONE",   "+371 20000000")
COMPANY_EMAIL   = _get("COMPANY_EMAIL",   "info@teikums.lv")
COMPANY_BANK    = _get("COMPANY_BANK",    "Swedbank")
COMPANY_IBAN    = _get("COMPANY_IBAN",    "LV00HABA0000000000000")

GDRIVE_CONFIGURED = bool(GDRIVE_CREDENTIALS_PATH and GDRIVE_FOLDER_ID)
