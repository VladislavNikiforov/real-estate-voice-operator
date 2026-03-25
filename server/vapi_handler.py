"""server/vapi_handler.py — Parse Vapi webhook payloads and route to orchestrator."""

import logging
from typing import Any

from llm import orchestrator

log = logging.getLogger(__name__)

# Map Vapi tool name → orchestrator handler
_HANDLERS = {
    "send_invoice":       orchestrator.handle_send_invoice,
    "send_reminder":      orchestrator.handle_send_reminder,
    "follow_up":          orchestrator.handle_follow_up,
    "request_documents":  orchestrator.handle_request_documents,
}


async def handle_tool_call(payload: dict) -> dict:
    """Parse a Vapi tool-call webhook and return a Vapi-formatted response.

    Vapi payload shape:
        {
          "message": {
            "type": "tool-calls",
            "toolCallList": [
              {"id": "call_abc", "type": "function",
               "function": {"name": "send_invoice", "arguments": {...}}}
            ]
          }
        }

    Returns:
        {"results": [{"toolCallId": "call_abc", "result": "Invoice sent..."}]}
    """
    results = []

    try:
        message = payload.get("message", {})
        msg_type = message.get("type", "")

        if msg_type != "tool-calls":
            log.info(f"Ignoring Vapi message type: {msg_type}")
            return {"results": []}

        tool_calls = message.get("toolCallList", [])
        log.info(f"Received {len(tool_calls)} tool call(s)")

        for call in tool_calls:
            call_id  = call.get("id", "unknown")
            fn       = call.get("function", {})
            name     = fn.get("name", "")
            args     = fn.get("arguments", {})

            log.info(f"Tool call [{call_id}]: {name}({list(args.keys())})")

            result_text = await _dispatch(name, args)
            results.append({"toolCallId": call_id, "result": result_text})

    except Exception as exc:
        log.error(f"vapi_handler error: {exc}", exc_info=True)
        results.append({
            "toolCallId": "error",
            "result": "Sorry, an internal error occurred. Please try again.",
        })

    return {"results": results}


async def _dispatch(tool_name: str, args: dict) -> str:
    handler = _HANDLERS.get(tool_name)
    if not handler:
        log.warning(f"Unknown tool: {tool_name}")
        return f"Unknown tool '{tool_name}'."

    try:
        result = await handler(args)
        if result.success:
            return result.message
        else:
            log.error(f"Pipeline failed for {tool_name}: {result.error}")
            return result.message
    except Exception as exc:
        log.error(f"Handler {tool_name} raised: {exc}", exc_info=True)
        return "Sorry, something went wrong. Please try again."
