"""server/app.py — FastAPI server: ElevenLabs post-call + Claude brain + dashboard."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse, Response

from server.elevenlabs_handler import handle_post_call

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Real Estate Voice Operator starting...")
    from server.config import ANTHROPIC_API_KEY, NOTION_TOKEN, CHROME_DEBUG_PORT
    log.info(f"   Claude brain  : {'configured' if ANTHROPIC_API_KEY else 'MISSING API KEY'}")
    log.info(f"   Notion        : {'configured' if NOTION_TOKEN else 'disabled (no token)'}")
    log.info(f"   sendmail_skill: Chrome debug port {CHROME_DEBUG_PORT}")
    yield
    log.info("Server shutting down.")


app = FastAPI(title="RE Voice Operator", lifespan=lifespan)


# ── POST /api/elevenlabs/post-call  ───────────────────────────
# Main entry point — ElevenLabs fires this after every call ends

@app.post("/api/elevenlabs/post-call")
async def elevenlabs_post_call(request: Request):
    """Receive ElevenLabs webhook events → route by type.

    ElevenLabs sends all events to this one URL:
      - conversation_initiation_client_data  → call starting (real-time)
      - post_call_transcription              → call ended, full transcript
      - (any other type)                     → logged, acknowledged
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    event_type = payload.get("type", "")
    log.info(f"ElevenLabs event type: {event_type!r}")

    # ── Call just started — immediately light up the dashboard ──
    if event_type in ("conversation_initiation_client_data", "call.initiated", "conversation.started"):
        from dashboard.events import emit_call_start
        conversation_id = (
            payload.get("conversation_id")
            or payload.get("data", {}).get("conversation_id", "live")
        )
        emit_call_start(conversation_id)
        log.info(f"Call started: {conversation_id}")
        return JSONResponse({"status": "ok", "event": "call_start"})

    # ── Post-call transcript — run full pipeline ─────────────────
    result = await handle_post_call(payload)
    log.info(f"Post-call result: {result}")
    return JSONResponse(result)


# ── POST /api/chat  ───────────────────────────────────────────
# Direct Claude brain — send text, get response with tool results

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Claude brain conversation endpoint.

    Body: {"session_id": "test", "text": "Send invoice to John for office rental"}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    session_id = body.get("session_id", "default")
    text = body.get("text", "").strip()
    if not text:
        return JSONResponse({"error": "no text provided"}, status_code=400)

    try:
        from brain.claude_brain import chat as claude_chat
        result = await claude_chat(session_id, text)
        return JSONResponse(result)
    except Exception as exc:
        log.error(f"chat error: {exc}", exc_info=True)
        return JSONResponse({"error": str(exc)}, status_code=500)


# ── POST /api/chat/reset  ─────────────────────────────────────

@app.post("/api/chat/reset")
async def chat_reset(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    session_id = body.get("session_id", "default")
    from brain.claude_brain import clear_session
    clear_session(session_id)
    return JSONResponse({"status": "ok", "session_id": session_id})


# ── POST /api/test/transcript  ────────────────────────────────
# Simulate a post-call webhook without making a real call

@app.post("/api/test/transcript")
async def test_transcript(request: Request):
    """Test the full transcript → Claude brain → pipeline flow.

    Example:
      {"transcript":[{"role":"user","message":"Send invoice to John, john@example.com, 1200 euros"}]}
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    result = await handle_post_call(payload)
    return JSONResponse(result)


# ── POST /api/elevenlabs/twilio-voice  ───────────────────────
# Twilio calls this when someone dials your number
# Returns TwiML that bridges the call to ElevenLabs agent

@app.post("/api/elevenlabs/twilio-voice")
async def twilio_voice(request: Request):
    """Twilio webhook — fires the instant someone calls. Bridge to ElevenLabs + real-time dashboard."""
    from twilio.twiml.voice_response import VoiceResponse, Connect
    from server.config import ELEVENLABS_AGENT_ID
    from dashboard.events import emit_call_start

    # Parse Twilio form body to get call metadata
    form = await request.form()
    call_sid = form.get("CallSid", "twilio-live")
    caller = form.get("From", "unknown")
    log.info(f"Incoming call: {caller} | SID: {call_sid}")

    # ── Immediately push "call active" to dashboard ───────────────
    emit_call_start(call_sid)

    response = VoiceResponse()
    response.say("Connecting you to the real estate assistant.")

    connect = Connect()
    stream_url = f"wss://api.elevenlabs.io/v1/convai/twilio?agent_id={ELEVENLABS_AGENT_ID}"
    connect.stream(url=stream_url)
    response.append(connect)

    return Response(content=str(response), media_type="application/xml")


# ── GET /dashboard  ───────────────────────────────────────────

@app.get("/dashboard")
async def dashboard():
    html_path = Path(__file__).parent.parent / "dashboard" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return JSONResponse({"error": "dashboard not found"}, status_code=404)


# ── GET /api/dashboard/state  ────────────────────────────────

@app.get("/api/dashboard/state")
async def dashboard_state():
    """Current stats + recent calls snapshot for dashboard initial load."""
    from dashboard.events import get_state
    return JSONResponse(get_state())


# ── GET /api/events  ──────────────────────────────────────────

@app.get("/api/events")
async def sse_events():
    """Server-Sent Events stream for the live dashboard."""
    from dashboard.events import subscribe, unsubscribe
    q = subscribe()

    async def event_stream():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=30)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield f": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe(q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── GET /health  ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "re-voice-operator"}
