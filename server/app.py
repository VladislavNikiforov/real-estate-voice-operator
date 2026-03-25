"""server/app.py — FastAPI webhook server for ElevenLabs Conversational AI."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from server.elevenlabs_handler import lookup_contact, search_emails, create_task
from brain.claude_brain import chat as claude_chat, clear_session

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Real Estate Voice Operator server starting...")
    from server.config import OPENCLAW_URL, GDRIVE_CONFIGURED
    log.info(f"   OpenClaw URL : {OPENCLAW_URL}")
    log.info(f"   Google Drive : {'configured' if GDRIVE_CONFIGURED else 'local fallback'}")
    yield
    log.info("Server shutting down.")


app = FastAPI(title="RE Voice Operator", lifespan=lifespan)


# ── ElevenLabs tool endpoints ─────────────────────────────────
# ElevenLabs sends a flat JSON body with just the parameters.
# Each tool gets its own URL configured in the ElevenLabs dashboard.

@app.post("/api/tools/lookup-contact")
async def tool_lookup_contact(request: Request):
    """ElevenLabs tool: find contact email by name."""
    try:
        params = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    log.info(f"[lookup-contact] params={params}")
    result = lookup_contact(params)
    log.info(f"[lookup-contact] result={result}")
    return JSONResponse(result)


@app.post("/api/tools/search-emails")
async def tool_search_emails(request: Request):
    """ElevenLabs tool: search recent emails."""
    try:
        params = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    log.info(f"[search-emails] params={params}")
    result = await search_emails(params)
    log.info(f"[search-emails] result={result}")
    return JSONResponse(result)


@app.post("/api/tools/create-task")
async def tool_create_task(request: Request):
    """ElevenLabs tool: create invoice/reminder/follow-up task."""
    try:
        params = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    log.info(f"[create-task] params={params}")
    result = await create_task(params)
    log.info(f"[create-task] result={result}")
    return JSONResponse(result)


# ── Claude brain endpoint ─────────────────────────────────────

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Claude-powered conversation. Send text, get response with tool results.

    Body: {"session_id": "...", "text": "Invoice Desktop Commander for 8 hours venue rental"}
    Response: {"text": "...", "actions_taken": [...]}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    session_id = body.get("session_id", "default")
    text = body.get("text", "").strip()

    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)

    log.info(f"[chat] session={session_id} text='{text[:80]}'")
    result = await claude_chat(session_id, text)
    log.info(f"[chat] response='{result['text'][:80]}' actions={len(result['actions_taken'])}")
    return JSONResponse(result)


@app.post("/api/chat/reset")
async def chat_reset(request: Request):
    """Reset a chat session."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    session_id = body.get("session_id", "default")
    clear_session(session_id)
    return JSONResponse({"status": "ok", "session_id": session_id})


# ── Manual test endpoint (same as before) ─────────────────────

@app.post("/api/test")
async def test_endpoint(request: Request):
    """Manual testing without ElevenLabs. Send a tool call directly.

    Example body:
        {
          "tool": "send_invoice",
          "params": {
            "client_name": "John Smith",
            "client_email": "john.smith@gmail.com",
            "property_id": "room-5",
            "amount": 240,
            "language": "en"
          }
        }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    tool = body.get("tool", "")
    params = body.get("params", {})

    if tool in ("lookup_contact", "lookup-contact"):
        result = lookup_contact(params)
    elif tool in ("search_emails", "search-emails"):
        result = await search_emails(params)
    elif tool in ("create_task", "create-task"):
        result = await create_task(params)
    else:
        # Legacy: treat tool name as an action for create_task
        params["action"] = tool
        result = await create_task(params)

    return JSONResponse({"tool": tool, "result": result})


# ── Health check ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "re-voice-operator"}
