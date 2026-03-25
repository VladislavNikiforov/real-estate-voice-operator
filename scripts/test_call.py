#!/usr/bin/env python3
"""Simulate a Vapi tool call locally — no phone needed.

Usage:
    python scripts/test_call.py                  # runs all 4 tools
    python scripts/test_call.py send_invoice     # test one tool
"""

import sys, os, asyncio, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

SERVER = os.getenv("SERVER_URL", "http://localhost:8000")

TEST_CALLS = [
    ("send_invoice", {
        "client_name":  "Jānis Bērziņš",
        "client_email": "janis@example.lv",
        "property_id":  "apt-3",
        "amount":       85000,
        "language":     "lv",
    }),
    ("send_invoice", {
        "client_name":  "Ivan Petrov",
        "client_email": "ivan@example.ru",
        "property_id":  "apt-5",
        "amount":       100000,
        "language":     "ru",
    }),
    ("send_reminder", {
        "client_name":  "John Smith",
        "client_email": "john@example.com",
        "property_id":  "apt-3",
        "amount":       85000,
        "language":     "en",
    }),
    ("follow_up", {
        "client_name":  "Anna Liepiņa",
        "client_email": "anna@example.lv",
        "property_id":  "house-1",
        "language":     "lv",
        "notes":        "Very interested in the garden.",
    }),
    ("request_documents", {
        "client_name":      "Maria Smirnova",
        "client_email":     "maria@example.ru",
        "documents_needed": "Паспорт, справка о доходах",
        "language":         "ru",
    }),
]

_C = "\033[96m"; _G = "\033[92m"; _Y = "\033[93m"; _R = "\033[91m"; _B = "\033[1m"; _N = "\033[0m"


def _make_vapi_payload(tool: str, args: dict) -> dict:
    return {
        "message": {
            "type": "tool-calls",
            "toolCallList": [{
                "id": f"test_{tool}",
                "type": "function",
                "function": {"name": tool, "arguments": args},
            }]
        }
    }


async def run_test(tool: str, args: dict) -> None:
    print(f"\n{_B}{_C}─── Testing: {tool} ───{_N}")
    print(f"  Params: {json.dumps(args, ensure_ascii=False, indent=2)[:200]}")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{SERVER}/api/vapi/tool-call",
                json=_make_vapi_payload(tool, args),
            )
        if resp.status_code == 200:
            result = resp.json()["results"][0]["result"]
            print(f"  {_G}✓ Result (Vapi speaks):{_N} \"{result}\"")
        else:
            print(f"  {_R}✗ HTTP {resp.status_code}: {resp.text[:200]}{_N}")
    except httpx.ConnectError:
        print(f"  {_R}✗ Could not connect to {SERVER} — is the server running?{_N}")
        print(f"    Run: python main.py  (in another terminal)")


async def main():
    filter_tool = sys.argv[1] if len(sys.argv) > 1 else None
    calls = [(t, a) for t, a in TEST_CALLS if not filter_tool or t == filter_tool]

    print(f"\n{_B}Real Estate Voice Operator — Tool Call Simulator{_N}")
    print(f"Target: {SERVER}")
    print(f"Running {len(calls)} test(s)...\n")

    for tool, args in calls:
        await run_test(tool, args)

    print(f"\n{_G}Done!{_N}\n")


if __name__ == "__main__":
    asyncio.run(main())
