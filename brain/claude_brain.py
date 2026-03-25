"""brain/claude_brain.py — Claude API conversation handler with tool execution loop."""

from __future__ import annotations

import json
import logging
from typing import Optional

import anthropic

from server.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from brain.system_prompt import SYSTEM_PROMPT, TOOLS
from brain.tools import execute_tool

log = logging.getLogger(__name__)

# ── Session store (in-memory for hackathon) ───────────────────
_sessions: dict[str, list[dict]] = {}


def _get_history(session_id: str) -> list[dict]:
    if session_id not in _sessions:
        _sessions[session_id] = []
    return _sessions[session_id]


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


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

    history = _get_history(session_id)
    history.append({"role": "user", "content": user_text})

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    actions_taken = []

    # Tool execution loop — Claude may call multiple tools before responding
    while True:
        log.info(f"[{session_id}] Calling Claude ({CLAUDE_MODEL})...")

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
        )

        log.info(f"[{session_id}] stop_reason={response.stop_reason}")

        # Collect all content blocks
        assistant_content = response.content

        # Add assistant response to history
        history.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "tool_use":
            # Execute each tool call and collect results
            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id

                    log.info(f"[{session_id}] Tool call: {tool_name}({json.dumps(tool_input, ensure_ascii=False)})")

                    result = await execute_tool(tool_name, tool_input)

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

            return {
                "text": response_text,
                "actions_taken": actions_taken,
            }

        else:
            # Unexpected stop reason
            log.warning(f"[{session_id}] Unexpected stop_reason: {response.stop_reason}")
            return {
                "text": "Sorry, something went wrong.",
                "actions_taken": actions_taken,
            }
