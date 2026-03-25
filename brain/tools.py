"""brain/tools.py — Execute tools called by Claude. Direct Python calls, no HTTP."""

from __future__ import annotations

import logging
from typing import Any

from notion.client import lookup_client as notion_lookup_client
from notion.client import lookup_service as notion_lookup_service
from llm.orchestrator import handle_send_invoice

log = logging.getLogger(__name__)


async def execute_tool(name: str, input_data: dict) -> Any:
    """Dispatch a tool call to the appropriate handler. Returns JSON-serializable result."""
    handler = _TOOLS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}

    try:
        return await handler(input_data)
    except Exception as exc:
        log.error(f"Tool {name} failed: {exc}", exc_info=True)
        return {"error": f"Tool execution failed: {str(exc)}"}


async def _handle_lookup_client(input_data: dict) -> dict:
    name = input_data.get("name", "")
    if not name:
        return {"error": "No name provided"}

    result = await notion_lookup_client(name)
    if not result:
        return {"error": f"No client found matching '{name}'"}

    return {
        "name": result.get("Nosaukums", ""),
        "reg_nr": result.get("Reģ. nr.", ""),
        "vat_nr": result.get("PVN nr.", ""),
        "address": result.get("Adrese", ""),
        "email": result.get("E-pasts", ""),
        "phone": result.get("Telefons", ""),
        "bank": result.get("Banka", ""),
        "iban": result.get("IBAN", ""),
        "payment_terms": result.get("Apmaksas termiņš", ""),
        "contact_person": result.get("Kontaktpersona", ""),
    }


async def _handle_lookup_service(input_data: dict) -> dict:
    name = input_data.get("name", "")
    if not name:
        return {"error": "No name provided"}

    result = await notion_lookup_service(name)
    if not result:
        return {"error": f"No service found matching '{name}'"}

    return {
        "name": result.get("Pakalpojums", ""),
        "description": result.get("Apraksts", ""),
        "unit": result.get("Mērvienība", ""),
        "rate_eur": result.get("Likme (EUR)", 0),
        "vat_rate": result.get("PVN likme (%)", 0),
        "category": result.get("Kategorija", ""),
    }


async def _handle_create_invoice(input_data: dict) -> dict:
    """Run the full invoice pipeline: PDF → Drive → Email."""
    params = {
        "client_name": input_data.get("client_name", ""),
        "service_name": input_data.get("service_name", ""),
        "quantity": input_data.get("quantity", 1),
        "language": input_data.get("language", "lv"),
        "notes": input_data.get("notes", ""),
    }

    result = await handle_send_invoice(params)

    return {
        "success": result.success,
        "invoice_number": result.invoice_number,
        "message": result.message,
        "drive_link": result.drive_link,
        "error": result.error,
    }


_TOOLS = {
    "lookup_client": _handle_lookup_client,
    "lookup_service": _handle_lookup_service,
    "create_invoice": _handle_create_invoice,
}
