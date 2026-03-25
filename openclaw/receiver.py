# openclaw/receiver.py
# ============================================================
# 🖥️ OWNER: @openclaw-person
# PURPOSE: HTTP server on VM — receives prompts from webhook server
# RUNS ON: The VM where OpenClaw + Desktop Commander are installed
# PORT: 8888
#
# Run:
#   pip install fastapi uvicorn
#   uvicorn openclaw.receiver:app --host 0.0.0.0 --port 8888
# ============================================================

import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="OpenClaw Receiver")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "openclaw-receiver"}


@app.post("/execute")
async def execute(request: Request):
    """
    Receive an OpenClawInstruction, pass prompt to Desktop Commander, return result.

    TODO(@openclaw-person): Replace placeholder with real Desktop Commander call.
    """
    start = time.monotonic()
    body  = await request.json()

    prompt = body.get("prompt", "")
    email  = body.get("email", {})

    print(f"\n[OpenClaw] Received instruction for: {email.get('to','')}")
    print(f"[OpenClaw] Subject: {email.get('subject','')}")
    print(f"[OpenClaw] Prompt preview: {prompt[:200]}...")

    # TODO(@openclaw-person): Call Desktop Commander here
    # result = await desktop_commander.execute(prompt)
    result = _placeholder_execute(prompt, email)

    elapsed = time.monotonic() - start
    return JSONResponse({**result, "execution_time": round(elapsed, 2)})


def _placeholder_execute(prompt: str, email: dict) -> dict:
    """
    TODO(@openclaw-person): Replace with real Desktop Commander integration.

    Real implementation should:
    1. from openclaw.desktop_commander import run_prompt
    2. return await run_prompt(prompt)
    """
    print("[OpenClaw] ⚠️  Placeholder — Desktop Commander not yet integrated")
    return {
        "success": False,
        "message": "TODO(@openclaw-person): integrate Desktop Commander",
    }
