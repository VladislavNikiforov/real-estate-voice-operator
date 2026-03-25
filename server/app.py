"""server/app.py — FastAPI webhook server for ElevenLabs Conversational AI."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from server.elevenlabs_handler import lookup_contact, search_emails, create_task

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Real Estate Voice Operator server starting...")
    from server.config import GDRIVE_CONFIGURED
    log.info(f"   Google Drive : {'configured' if GDRIVE_CONFIGURED else 'local fallback'}")
    log.info(f"   Email send   : Gmail API (OAuth2)")
    yield
    log.info("Server shutting down.")


app = FastAPI(title="RE Voice Operator", lifespan=lifespan)


# ── ElevenLabs tool endpoints ─────────────────────────────────

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


# ── Manual test endpoint ──────────────────────────────────────

@app.post("/api/test")
async def test_endpoint(request: Request):
    """Manual testing without ElevenLabs. Send a tool call directly."""
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
        params["action"] = tool
        result = await create_task(params)

    return JSONResponse({"tool": tool, "result": result})


# ── Health check ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "re-voice-operator"}
