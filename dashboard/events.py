"""dashboard/events.py — SSE event bus + stats tracking for live pipeline dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
import time

log = logging.getLogger(__name__)

_clients: list[asyncio.Queue] = []

_stats = {
    "calls_today": 0,
    "invoices_sent": 0,
    "emails_sent": 0,
    "notion_creates": 0,
}

_calls: list[dict] = []


def get_stats() -> dict:
    return dict(_stats)


def get_calls() -> list[dict]:
    return list(_calls[-20:])


def get_state() -> dict:
    return {"stats": get_stats(), "calls": get_calls()}


def _broadcast(event_type: str, data: dict) -> None:
    payload = json.dumps({"type": event_type, "ts": time.time(), **data}, ensure_ascii=False)
    for q in list(_clients):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _clients.append(q)
    log.info(f"Dashboard client connected ({len(_clients)} total)")
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    if q in _clients:
        _clients.remove(q)
    log.info(f"Dashboard client disconnected ({len(_clients)} total)")


def emit_call_start(conversation_id: str) -> None:
    # Deduplicate — Twilio webhook and ElevenLabs start event may both fire
    if any(c["id"] == conversation_id for c in _calls):
        _broadcast("call_start", {"conversation_id": conversation_id, "stats": get_stats()})
        return
    _stats["calls_today"] += 1
    _calls.append({"id": conversation_id, "started_at": time.strftime("%H:%M:%S"), "status": "active", "actions": []})
    _broadcast("call_start", {"conversation_id": conversation_id, "stats": get_stats()})


def emit_call_end(conversation_id: str, success: bool) -> None:
    for c in _calls:
        if c["id"] == conversation_id:
            c["status"] = "done" if success else "failed"
            c["ended_at"] = time.strftime("%H:%M:%S")
    _broadcast("call_end", {"conversation_id": conversation_id, "success": success, "stats": get_stats()})


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
    _stats["invoices_sent"] += 1
    _broadcast("invoice", {"invoice_number": invoice_number, "total": total, "client": client, "drive_link": drive_link, "stats": get_stats()})


def emit_email_sent(to: str, subject: str, success: bool) -> None:
    if success:
        _stats["emails_sent"] += 1
    _broadcast("email_sent", {"to": to, "subject": subject, "success": success, "stats": get_stats()})


def emit_notion_update(action: str, name: str, detail: str = "") -> None:
    if action == "created":
        _stats["notion_creates"] += 1
    _broadcast("notion_update", {"action": action, "name": name, "detail": detail, "stats": get_stats()})


def emit_error(message: str) -> None:
    _broadcast("error", {"message": message})


def emit_reset() -> None:
    _broadcast("reset", {})
