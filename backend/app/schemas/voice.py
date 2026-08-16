from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.ai.orchestrator.schemas import (
    MAX_MESSAGE_LENGTH,
    AvatarHint,
    ToolCallRecord,
)

# Voice input mirrors the chat message contract. Identity/role never come from
# the client — they are resolved from the authenticated caller (or, for the
# Vapi webhook, from trusted call metadata).
class VoiceTurnRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    conversation_id: Optional[str] = None
    transcript: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    # Optional language hint, applied only when a NEW conversation is created.
    # Affects phrasing only, never authorization.
    language: Optional[str] = None


class VoiceReply(BaseModel):
    """TTS-ready response for a voice turn. `say` is the text Vapi speaks."""

    model_config = ConfigDict(extra="ignore")

    conversation_id: str
    text: str
    say: str
    language: str
    persona: str
    tool_calls: List[ToolCallRecord] = []
    avatar: AvatarHint = AvatarHint()
