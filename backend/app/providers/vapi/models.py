from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

# Vapi server-message (webhook) event types we care about. Others are treated as
# informational and acknowledged without invoking the orchestrator.
EVENT_TOOL_CALLS = "tool-calls"
EVENT_TRANSCRIPT = "transcript"


class NormalizedVoiceEvent(BaseModel):
    """Provider-neutral view of a Vapi voice event.

    The webhook normalizer produces this so the rest of the backend never parses
    raw Vapi payloads. Identity (`firebase_uid`) and `language` are taken ONLY
    from the call's trusted server-side metadata (set by us when the call is
    created), never from the caller's spoken words.
    """

    model_config = ConfigDict(extra="ignore")

    event_type: str
    call_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

    # Present only when this event should produce a spoken reply.
    transcript: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None

    # Propagated from trusted call metadata.
    language: Optional[str] = None
    conversation_id: Optional[str] = None
    firebase_uid: Optional[str] = None

    # Whether the orchestrator should be invoked for this event.
    requires_reply: bool = False
