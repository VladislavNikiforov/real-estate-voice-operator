"""server/app.py — FastAPI webhook server."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from server.vapi_handler import handle_tool_call

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Real Estate Voice Operator server starting...")
    from server.config import OPENCLAW_URL, GDRIVE_CONFIGURED
    log.info(f"   OpenClaw URL : {OPENCLAW_URL}")
    log.info(f"   Google Drive : {'configured ✓' if GDRIVE_CONFIGURED else 'local fallback'}")
    yield
    log.info("Server shutting down.")


app = FastAPI(title="RE Voice Operator", lifespan=lifespan)


# ── POST /api/vapi/tool-call  ─────────────────────────────────

@app.post("/api/vapi/tool-call")
async def vapi_tool_call(request: Request):
    """Vapi calls this when the assistant invokes a tool."""
    try:
        payload = await request.json()
        log.debug(f"Vapi payload: {payload}")
    except Exception:
        return JSONResponse({"results": [{"toolCallId": "err", "result": "Bad request — invalid JSON"}]}, status_code=400)

    response = await handle_tool_call(payload)
    log.debug(f"Vapi response: {response}")
    return JSONResponse(response)


# ── POST /api/test  ───────────────────────────────────────────

@app.post("/api/test")
async def test_endpoint(request: Request):
    """Manual testing without Vapi. Send a tool call directly.

    Example body:
        {
          "tool": "send_invoice",
          "params": {
            "client_name": "Jānis Bērziņš",
            "client_email": "janis@example.com",
            "property_id": "apt-3",
            "amount": 85000,
            "language": "lv"
          }
        }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    tool   = body.get("tool", "")
    params = body.get("params", {})

    # Wrap as a Vapi payload so we reuse the same handler
    vapi_payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [{
                "id": "test_call",
                "type": "function",
                "function": {"name": tool, "arguments": params},
            }]
        }
    }

    result = await handle_tool_call(vapi_payload)
    spoken = result["results"][0]["result"] if result.get("results") else ""
    return JSONResponse({"tool": tool, "result": spoken})


# ── GET /health  ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "re-voice-operator"}
