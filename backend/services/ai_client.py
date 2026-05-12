"""Shared AI helper for V11 modules.

Uses emergentintegrations (Emergent LLM key).

MODEL NOTE (2026-04-19): OpenAI gpt-5.2 upstream was persistently 502'ing during
V11 validation, so V11 generation was switched to claude-sonnet-4.5 as a fallback.
V1-V10 remain on gpt-5.2 (see server.py::call_ai). To revert V11 to gpt-5.2:
    chat.with_model("openai", "gpt-5.2")
"""
import asyncio
import json
import logging
import re
import uuid

from fastapi import HTTPException

from deps import EMERGENT_LLM_KEY

logger = logging.getLogger(__name__)

# Total wall-clock budget for a single AI call (seconds).
AI_CALL_TIMEOUT = 60

# V11-only model. Swap this line to restore gpt-5.2 when OpenAI upstream recovers.
# Options (all covered by EMERGENT_LLM_KEY):
#   ("anthropic", "claude-sonnet-4-5-20250929")  <-- current (cheap + reliable + short, good for WhatsApp/social)
#   ("gemini",    "gemini-3.1-pro-preview")      <-- fallback #2
#   ("openai",    "gpt-5.2")                     <-- original, restore when healthy
V11_AI_PROVIDER = "anthropic"
V11_AI_MODEL = "claude-sonnet-4-5-20250929"


async def call_ai(system_msg: str, user_msg: str) -> str:
    """Send a single message using the V11 fallback model.

    Raises HTTPException(503) if the upstream times out or errors, or if
    EMERGENT_LLM_KEY is not configured.
    """
    if not EMERGENT_LLM_KEY:
        raise HTTPException(
            status_code=503,
            detail="AI is not configured. Set EMERGENT_LLM_KEY in backend/.env and restart.",
        )
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=str(uuid.uuid4()),
        system_message=system_msg,
    )
    chat.with_model(V11_AI_PROVIDER, V11_AI_MODEL)
    try:
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=user_msg)),
            timeout=AI_CALL_TIMEOUT,
        )
        return response
    except asyncio.TimeoutError:
        logger.warning("AI call timed out after %ss — upstream likely degraded.", AI_CALL_TIMEOUT)
        raise HTTPException(
            status_code=503,
            detail="AI service is slow to respond. Please try again in a moment.",
        )
    except Exception as e:
        logger.error("AI call failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Please try again.",
        )


def extract_json(text: str) -> dict:
    """Best-effort JSON extraction from an AI response."""
    if not text:
        return {}
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try to find the first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {}
