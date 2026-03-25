"""mock/mock_openclaw.py — Fake OpenClaw VM endpoint.

Receives an OpenClawInstruction, prints the prompt beautifully, returns success.

Run standalone:
    python -m mock.mock_openclaw
"""

import asyncio
import time
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock OpenClaw")

_G = "\033[92m"   # green
_C = "\033[96m"   # cyan
_Y = "\033[93m"   # yellow
_B = "\033[1m"    # bold
_R = "\033[0m"    # reset

_log: list[dict] = []


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-openclaw", "requests": len(_log)}


@app.post("/execute")
async def execute(request: Request):
    start = time.monotonic()
    body = await request.json()
    _log.append({"ts": datetime.utcnow().isoformat(), "body": body})

    email  = body.get("email", {})
    prompt = body.get("prompt", "(no prompt)")
    action = body.get("action", "?")

    print(f"\n{_B}{_G}{'═'*62}{_R}")
    print(f"{_B}{_G}  🖥️  MOCK OPENCLAW — INSTRUCTION RECEIVED{_R}")
    print(f"{_G}{'═'*62}{_R}")
    print(f"  {_C}Action:{_R}   {action}")
    print(f"  {_C}To:{_R}       {email.get('to','')}")
    print(f"  {_C}Subject:{_R}  {email.get('subject','')}")
    print(f"  {_C}Language:{_R} {email.get('language','')}")
    if email.get("drive_link"):
        print(f"  {_C}Link:{_R}     {email.get('drive_link')}")
    print(f"\n  {_Y}Prompt for Desktop Commander:{_R}")
    print("─" * 62)
    for line in prompt.strip().split("\n"):
        print(f"  {line}")
    print(f"{_G}{'═'*62}{_R}\n")

    await asyncio.sleep(1.5)  # simulate execution time
    elapsed = time.monotonic() - start

    return JSONResponse({
        "success": True,
        "message": f"Mock: email to {email.get('to','')} queued for sending",
        "execution_time": round(elapsed, 2),
    })


@app.get("/log")
async def get_log():
    return {"count": len(_log), "entries": _log}


if __name__ == "__main__":
    print(f"{_B}{_C}Starting Mock OpenClaw on port 8888...{_R}\n")
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="warning")
