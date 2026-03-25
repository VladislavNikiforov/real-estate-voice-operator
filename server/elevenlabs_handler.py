"""server/elevenlabs_handler.py — Handle ElevenLabs Conversational AI webhook tool calls.

ElevenLabs server tools send a flat JSON body with just the parameters
the LLM extracted from conversation. Each tool has its own endpoint URL.
Response is a JSON object that the agent reads back to the user.
"""

import json
import logging
import os
from typing import Any

from llm import orchestrator

log = logging.getLogger(__name__)

# ── Contact lookup (from contacts.json) ───────────────────────

_CONTACTS: list[dict] = []


def _load_contacts() -> list[dict]:
    global _CONTACTS
    if _CONTACTS:
        return _CONTACTS
    try:
        path = os.path.join(os.path.dirname(__file__), "..", "data", "contacts.json")
        with open(path, "r", encoding="utf-8") as f:
            _CONTACTS = json.load(f)
        log.info(f"Loaded {len(_CONTACTS)} contacts")
    except FileNotFoundError:
        log.warning("data/contacts.json not found — lookup_contact will return empty")
        _CONTACTS = []
    except Exception as exc:
        log.error(f"Failed to load contacts: {exc}")
        _CONTACTS = []
    return _CONTACTS


def lookup_contact(params: dict) -> dict:
    """Find a contact by name (fuzzy match)."""
    name = params.get("name", "").strip().lower()
    if not name:
        return {"error": "No name provided"}

    contacts = _load_contacts()
    for c in contacts:
        full = c.get("full_name", "").lower()
        if name in full or full in name:
            return {"full_name": c["full_name"], "email": c["email"]}

    # Partial match on first or last name
    for c in contacts:
        parts = c.get("full_name", "").lower().split()
        if any(name in p or p in name for p in parts):
            return {"full_name": c["full_name"], "email": c["email"]}

    return {"error": f"No contact found for '{params.get('name', '')}'"}


# ── Search emails (placeholder — will use Gmail API when connected) ──

async def search_emails(params: dict) -> dict:
    """Search emails. Currently returns mock data.
    TODO: Replace with real Gmail API calls when OAuth2 is configured.
    """
    query = params.get("query", "")
    log.info(f"search_emails: query='{query}'")

    # Mock response for demo — replace with Gmail API
    return {
        "emails": [
            {
                "from": "john.smith@gmail.com",
                "subject": "Office Room 5 Booking",
                "snippet": "Hi, I'd like to book Room 5 for March 27-29. Please send me the invoice.",
                "date": "2026-03-24",
            }
        ],
        "note": "Mock data — connect Gmail API for real results",
    }


# ── Create task (triggers the full pipeline) ─────────────────

_HANDLERS = {
    "send_invoice": orchestrator.handle_send_invoice,
    "send_reminder": orchestrator.handle_send_reminder,
    "follow_up": orchestrator.handle_follow_up,
    "request_documents": orchestrator.handle_request_documents,
}


async def create_task(params: dict) -> dict:
    """Create an async task. Dispatches to the orchestrator pipeline."""
    action = params.get("action", "send_invoice")
    handler = _HANDLERS.get(action)

    if not handler:
        return {"task_id": "none", "status": "error", "message": f"Unknown action: {action}"}

    log.info(f"create_task: action={action}, params={list(params.keys())}")

    try:
        result = await handler(params)
        return {
            "task_id": result.invoice_number or f"task-{action}",
            "status": "completed" if result.success else "failed",
            "message": result.message,
            "drive_link": result.drive_link,
        }
    except Exception as exc:
        log.error(f"create_task failed: {exc}", exc_info=True)
        return {
            "task_id": "error",
            "status": "error",
            "message": "Sorry, something went wrong processing your request.",
        }
