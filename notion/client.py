"""notion/client.py — Notion API client for Clients and Services databases."""

from __future__ import annotations

import logging
from typing import Optional, List, Dict

import httpx

from server.config import NOTION_TOKEN, NOTION_CLIENTS_DB, NOTION_SERVICES_DB

log = logging.getLogger(__name__)

_NOTION_API = "https://api.notion.com/v1"
_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


# ── Property extractors ──────────────────────────────────────

def _extract_title(prop: dict) -> str:
    items = prop.get("title", [])
    return items[0]["plain_text"] if items else ""


def _extract_rich_text(prop: dict) -> str:
    items = prop.get("rich_text", [])
    return items[0]["plain_text"] if items else ""


def _extract_email(prop: dict) -> str:
    return prop.get("email", "") or ""


def _extract_phone(prop: dict) -> str:
    return prop.get("phone_number", "") or ""


def _extract_number(prop: dict) -> Optional[float]:
    return prop.get("number")


def _extract_select(prop: dict) -> str:
    sel = prop.get("select")
    return sel["name"] if sel else ""


def _parse_properties(props: dict) -> dict:
    """Parse Notion property objects into a flat dict."""
    result = {}
    for key, val in props.items():
        ptype = val.get("type", "")
        if ptype == "title":
            result[key] = _extract_title(val)
        elif ptype == "rich_text":
            result[key] = _extract_rich_text(val)
        elif ptype == "email":
            result[key] = _extract_email(val)
        elif ptype == "phone_number":
            result[key] = _extract_phone(val)
        elif ptype == "number":
            result[key] = _extract_number(val)
        elif ptype == "select":
            result[key] = _extract_select(val)
    return result


# ── Query helpers ─────────────────────────────────────────────

async def _query_db(database_id: str, filter_payload: Optional[Dict] = None) -> List[Dict]:
    """Query a Notion database and return parsed rows."""
    body = {}
    if filter_payload:
        body["filter"] = filter_payload

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_NOTION_API}/databases/{database_id}/query",
            headers=_HEADERS,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    return [_parse_properties(page["properties"]) for page in data.get("results", [])]


# ── Public API ────────────────────────────────────────────────

async def lookup_client(name: str) -> Optional[dict]:
    """Find a client by name (contains match). Returns first match or None."""
    if not NOTION_TOKEN or not NOTION_CLIENTS_DB:
        log.warning("Notion not configured — cannot look up client")
        return None

    rows = await _query_db(NOTION_CLIENTS_DB, {
        "property": "Nosaukums",
        "title": {"contains": name},
    })

    if not rows:
        log.info(f"No client found matching '{name}'")
        return None

    log.info(f"Found client: {rows[0].get('Nosaukums', 'unknown')}")
    return rows[0]


async def lookup_service(name: str) -> Optional[dict]:
    """Find a service by name (contains match). Returns first match or None."""
    if not NOTION_TOKEN or not NOTION_SERVICES_DB:
        log.warning("Notion not configured — cannot look up service")
        return None

    rows = await _query_db(NOTION_SERVICES_DB, {
        "property": "Pakalpojums",
        "title": {"contains": name},
    })

    if not rows:
        log.info(f"No service found matching '{name}'")
        return None

    log.info(f"Found service: {rows[0].get('Pakalpojums', 'unknown')}")
    return rows[0]


async def list_clients() -> list[dict]:
    """List all active clients."""
    return await _query_db(NOTION_CLIENTS_DB, {
        "property": "Status",
        "select": {"equals": "Aktīvs"},
    })


async def list_services() -> list[dict]:
    """List all active services."""
    return await _query_db(NOTION_SERVICES_DB, {
        "property": "Status",
        "select": {"equals": "Aktīvs"},
    })
