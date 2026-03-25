"""server/elevenlabs_handler.py — ElevenLabs post-call webhook handler.

Flow:
  POST /api/elevenlabs/post-call
    → extract transcript text
    → feed to claude_brain.chat()
    → Claude calls: lookup_client (Notion) → create_invoice
    → create_invoice: PDF + sendmail_skill → Gmail
"""

import logging

log = logging.getLogger(__name__)


def extract_transcript(payload: dict) -> str:
    """Defensively extract transcript text from ElevenLabs post-call payload.

    Handles all known shapes:
      payload["data"]["transcript"]       ← ElevenLabs wrapped
      payload["transcript"]               ← ElevenLabs flat
      payload["conversation"]["messages"] ← alternative
      payload["messages"]                 ← fallback
    """
    print("RAW PAYLOAD KEYS:", list(payload.keys()))

    # Unwrap "data" envelope if present
    inner = payload.get("data", payload)

    messages = []

    if "transcript" in inner and isinstance(inner["transcript"], list):
        messages = inner["transcript"]
        log.info(f"Transcript format: ElevenLabs native ({len(messages)} turns)")

    elif "conversation" in inner:
        conv = inner["conversation"]
        if isinstance(conv, dict) and "messages" in conv:
            messages = conv["messages"]
            log.info(f"Transcript format: conversation.messages ({len(messages)} turns)")

    elif "messages" in inner and isinstance(inner["messages"], list):
        messages = inner["messages"]
        log.info(f"Transcript format: top-level messages ({len(messages)} turns)")

    if not messages:
        log.warning(f"No transcript found. Full payload: {payload}")
        return ""

    lines = []
    for turn in messages:
        role = turn.get("role", "unknown").upper()
        text = turn.get("message") or turn.get("content") or ""
        if text:
            lines.append(f"{role}: {text}")

    transcript = "\n".join(lines)
    print("EXTRACTED TRANSCRIPT:", transcript)
    return transcript


async def handle_post_call(payload: dict) -> dict:
    """Receive ElevenLabs post-call transcript and run the full pipeline via Claude brain.

    Claude brain handles:
      1. lookup_client in Notion
      2. create_invoice → PDF + sendmail_skill email
    """
    conversation_id = payload.get("conversation_id") or payload.get("data", {}).get("conversation_id", "unknown")
    print("=" * 60)
    print("ELEVENLABS POST-CALL | conversation_id:", conversation_id)
    print("=" * 60)

    # ── 1. Extract transcript ─────────────────────────────────
    transcript = extract_transcript(payload)
    if not transcript:
        log.warning("Empty transcript — nothing to process")
        return {"status": "skipped", "reason": "empty transcript"}

    # ── 2. Feed to Claude brain ───────────────────────────────
    try:
        from brain.claude_brain import chat as claude_chat
        result = await claude_chat(session_id=conversation_id, user_text=transcript)
        log.info(f"Claude brain result: {result['text'][:100]} | actions={len(result['actions_taken'])}")
        return {
            "status": "processed",
            "response": result["text"],
            "actions_taken": len(result["actions_taken"]),
        }
    except Exception as exc:
        log.error(f"Claude brain failed: {exc}", exc_info=True)
        return {"status": "error", "reason": str(exc)}
