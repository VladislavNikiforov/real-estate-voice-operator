"""brain/claude_brain.py — Claude API conversation handler with tool execution loop."""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

import anthropic

from server.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from brain.system_prompt import SYSTEM_PROMPT, TOOLS
from brain.tools import execute_tool
from dashboard.events import (
    emit_transcript, emit_step_start, emit_step_done,
    emit_step_waiting, emit_response, emit_invoice, emit_reset,
)

log = logging.getLogger(__name__)

# ── Session store (in-memory for hackathon) ───────────────────
_sessions: dict[str, list[dict]] = {}


def _get_history(session_id: str) -> list[dict]:
    if session_id not in _sessions:
        _sessions[session_id] = []
    return _sessions[session_id]


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    emit_reset()


# ── Main conversation handler ─────────────────────────────────

async def chat(session_id: str, user_text: str) -> dict:
    """Process a user message through Claude with tool execution.

    Returns:
        {
            "text": "Claude's response to speak back",
            "actions_taken": [{"tool": "...", "input": {...}, "result": {...}}, ...],
        }
    """
    if not ANTHROPIC_API_KEY:
        return {"text": "Claude API key not configured.", "actions_taken": []}

    emit_transcript(session_id, user_text)

    history = _get_history(session_id)
    history.append({"role": "user", "content": user_text})

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    actions_taken = []

    emit_step_start("parse", "Parse intent")

    # Tool execution loop — Claude may call multiple tools before responding
    while True:
        log.info(f"[{session_id}] Calling Claude ({CLAUDE_MODEL})...")
        t0 = time.time()

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
        )

        llm_ms = int((time.time() - t0) * 1000)
        log.info(f"[{session_id}] stop_reason={response.stop_reason} ({llm_ms}ms)")

        # Collect all content blocks
        assistant_content = response.content

        # Add assistant response to history
        history.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "tool_use":
            emit_step_done("parse", "Parse intent", f"Claude decided tools", llm_ms)

            # Execute each tool call and collect results
            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id

                    _label = _tool_label(tool_name)
                    emit_step_start(tool_name, _label, json.dumps(tool_input, ensure_ascii=False)[:100])

                    log.info(f"[{session_id}] Tool call: {tool_name}({json.dumps(tool_input, ensure_ascii=False)})")

                    t1 = time.time()
                    result = await execute_tool(tool_name, tool_input)
                    tool_ms = int((time.time() - t1) * 1000)

                    detail = _tool_detail(tool_name, result)
                    emit_step_done(tool_name, _label, detail, tool_ms)

                    # Emit invoice preview if create_invoice succeeded
                    if tool_name == "create_invoice" and result.get("success"):
                        from pdf_generator.templates import format_amount
                        emit_invoice(
                            result.get("invoice_number", ""),
                            format_amount(float(result.get("message", "0").split("par ")[-1].split(" ")[0].replace("\xa0", "").replace(",", ".")), "EUR", "lv") if result.get("invoice_number") else "",
                            tool_input.get("client_name", ""),
                            result.get("drive_link", ""),
                        )

                    log.info(f"[{session_id}] Tool result: {json.dumps(result, ensure_ascii=False)[:200]}")

                    actions_taken.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": result,
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

            # Add tool results to history and loop back for Claude's next response
            history.append({"role": "user", "content": tool_results})
            continue

        elif response.stop_reason == "end_turn":
            # Extract text response
            text_parts = []
            for block in assistant_content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)

            response_text = " ".join(text_parts) if text_parts else ""
            log.info(f"[{session_id}] Response: {response_text[:100]}")

            # Check if Claude is waiting for confirmation
            if any(w in response_text.lower() for w in ["apstiprināt", "confirm", "proceed", "shall i", "vai"]):
                emit_step_waiting("confirm", "Confirm with user", response_text[:120])
            else:
                emit_step_done("parse", "Parse intent", "", llm_ms)

            emit_response(session_id, response_text)

            return {
                "text": response_text,
                "actions_taken": actions_taken,
            }

        else:
            log.warning(f"[{session_id}] Unexpected stop_reason: {response.stop_reason}")
            return {
                "text": "Sorry, something went wrong.",
                "actions_taken": actions_taken,
            }


def _tool_label(name: str) -> str:
    return {
        "lookup_client": "Lookup client",
        "lookup_service": "Lookup service",
        "create_invoice": "Create invoice",
    }.get(name, name)


def _tool_detail(name: str, result: dict) -> str:
    if name == "lookup_client":
        if "error" in result:
            return result["error"]
        return f"{result.get('name', '')} — {result.get('email', '')}"
    elif name == "lookup_service":
        if "error" in result:
            return result["error"]
        return f"{result.get('name', '')} — {result.get('rate_eur', 0)} EUR/{result.get('unit', '')}"
    elif name == "create_invoice":
        if result.get("success"):
            return f"{result.get('invoice_number', '')} sent"
        return result.get("error", "failed")
    return json.dumps(result, ensure_ascii=False)[:80]
