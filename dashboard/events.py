"""dashboard/events.py — SSE event bus for live pipeline dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

log = logging.getLogger(__name__)

# Connected SSE clients
_clients: list[asyncio.Queue] = []


def _broadcast(event_type: str, data: dict) -> None:
    """Send event to all connected dashboard clients."""
    payload = json.dumps({"type": event_type, "ts": time.time(), **data}, ensure_ascii=False)
    for q in _clients:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


def subscribe() -> asyncio.Queue:
    """Register a new SSE client. Returns a queue to read events from."""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _clients.append(q)
    log.info(f"Dashboard client connected ({len(_clients)} total)")
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    """Remove an SSE client."""
    _clients.remove(q)
    log.info(f"Dashboard client disconnected ({len(_clients)} total)")


# ── Public event emitters ─────────────────────────────────────

def emit_transcript(session_id: str, text: str) -> None:
    _broadcast("transcript", {"session_id": session_id, "text": text})


def emit_step_start(step: str, label: str, detail: str = "") -> None:
    _broadcast("step_start", {"step": step, "label": label, "detail": detail})


def emit_step_done(step: str, label: str, detail: str = "", duration_ms: int = 0) -> None:
    _broadcast("step_done", {"step": step, "label": label, "detail": detail, "duration_ms": duration_ms})


def emit_step_waiting(step: str, label: str, detail: str = "") -> None:
    _broadcast("step_waiting", {"step": step, "label": label, "detail": detail})


def emit_response(session_id: str, text: str) -> None:
    _broadcast("response", {"session_id": session_id, "text": text})


def emit_invoice(invoice_number: str, total: str, client: str, drive_link: str = "") -> None:
    _broadcast("invoice", {
        "invoice_number": invoice_number,
        "total": total,
        "client": client,
        "drive_link": drive_link,
    })


def emit_error(message: str) -> None:
    _broadcast("error", {"message": message})


def emit_reset() -> None:
    _broadcast("reset", {})
