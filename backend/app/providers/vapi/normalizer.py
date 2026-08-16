import json
from typing import Any, Dict, Optional

from app.ai.orchestrator.schemas import ChatResponse
from app.core.config import settings
from app.providers.vapi.errors import VapiError
from app.providers.vapi.models import (
    EVENT_TOOL_CALLS,
    EVENT_TRANSCRIPT,
    NormalizedVoiceEvent,
)

# Bound the text we hand back to Vapi for TTS so a runaway model answer cannot
# flood the voice channel.
_MAX_SPEECH_LENGTH = 1500

# Safe, non-revealing messages spoken when voice processing fails. They never
# contain user data, tool names, or error internals.
_SAFE_MESSAGES = {
    "unavailable": "I'm sorry, I couldn't process that right now. Please try again later.",
    "account_unidentified": "I couldn't identify your account. Please use the app or contact the school.",
    "account_error": "I'm sorry, there was a problem with your account. Please try again later.",
}


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _inner_message(raw: Any) -> Dict[str, Any]:
    """Vapi wraps events as `{"message": {...}}`; tolerate unwrapped bodies."""
    if not isinstance(raw, dict):
        raise VapiError("Malformed webhook payload", code="INVALID_EVENT", status_code=400)
    message = raw.get("message", raw)
    if not isinstance(message, dict):
        raise VapiError("Malformed webhook payload", code="INVALID_EVENT", status_code=400)
    return message


def normalize_event(
    raw: Any, *, voice_tool_name: Optional[str] = None
) -> NormalizedVoiceEvent:
    """Translate a raw Vapi webhook payload into a `NormalizedVoiceEvent`.

    Design: Vapi performs STT only; this backend is the brain. The assistant is
    configured with a single tool (`VAPI_VOICE_TOOL_NAME`) whose parameter is the
    user's transcript. When Vapi decides to call it, we run the orchestrator and
    return the spoken reply. `transcript` events are informational and never
    trigger a reply (that would bypass our orchestrator as the brain).
    """
    tool_name = voice_tool_name or settings.VAPI_VOICE_TOOL_NAME
    message = _inner_message(raw)

    event_type = message.get("type")
    call = message.get("call") or {}
    if not isinstance(call, dict):
        call = {}
    call_id = _as_str(call.get("id"))

    metadata = call.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    # Identity + language come strictly from server-side call metadata, never
    # from the spoken transcript.
    firebase_uid = _as_str(metadata.get("user_id")) or _as_str(
        metadata.get("firebase_uid")
    )
    language = _as_str(metadata.get("language"))
    conversation_id = _as_str(metadata.get("conversation_id"))

    if event_type == EVENT_TOOL_CALLS:
        calls = message.get("toolCallList") or []
        target = None
        for item in calls:
            if isinstance(item, dict) and item.get("name") == tool_name:
                target = item
                break

        if target is None:
            # No voice tool in this batch; acknowledge only.
            return NormalizedVoiceEvent(
                event_type=event_type,
                call_id=call_id,
                metadata=metadata,
                language=language,
                conversation_id=conversation_id,
                firebase_uid=firebase_uid,
                requires_reply=False,
            )

        params = target.get("parameters") or {}
        transcript = (
            _as_str(params.get("transcript"))
            or _as_str(params.get("speech"))
            or _as_str(params.get("message"))
        )
        return NormalizedVoiceEvent(
            event_type=event_type,
            call_id=call_id,
            metadata=metadata,
            transcript=transcript,
            tool_call_id=_as_str(target.get("id")),
            tool_name=tool_name,
            language=language,
            conversation_id=conversation_id,
            firebase_uid=firebase_uid,
            requires_reply=True,
        )

    if isinstance(event_type, str) and event_type.startswith(EVENT_TRANSCRIPT):
        # Informational STT update; the brain runs on the tool-call instead.
        return NormalizedVoiceEvent(
            event_type=event_type,
            call_id=call_id,
            metadata=metadata,
            language=language,
            conversation_id=conversation_id,
            firebase_uid=firebase_uid,
            requires_reply=False,
        )

    # Any other informational event (status-update, end-of-call-report, ...).
    return NormalizedVoiceEvent(
        event_type=str(event_type),
        call_id=call_id,
        metadata=metadata,
        language=language,
        conversation_id=conversation_id,
        firebase_uid=firebase_uid,
        requires_reply=False,
    )


def resolve_conversation_id(event: NormalizedVoiceEvent) -> str:
    """Pick a stable conversation id for the turn.

    Prefers an explicit id from trusted call metadata; otherwise derives one from
    the call id so every turn of the same phone call shares a conversation.
    """
    if event.conversation_id:
        return event.conversation_id
    if event.call_id:
        return f"vapi:{event.call_id}"
    return "vapi:anonymous"


def normalize_response(
    event: NormalizedVoiceEvent,
    chat_response: ChatResponse,
    *,
    voice_tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Map a `ChatResponse` into the `results` payload Vapi expects.

    Vapi speaks the `result` text of the matching tool call.
    """
    tool_name = voice_tool_name or settings.VAPI_VOICE_TOOL_NAME
    spoken = (chat_response.text or "").strip()[:_MAX_SPEECH_LENGTH]
    return {
        "results": [
            {
                "name": event.tool_name or tool_name,
                "toolCallId": event.tool_call_id or "",
                "result": spoken or safe_message("unavailable"),
            }
        ]
    }


def safe_message(kind: str) -> str:
    """Return a safe, TTS-ready message for a failure mode."""
    return _SAFE_MESSAGES.get(kind, _SAFE_MESSAGES["unavailable"])
