from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.ai.orchestrator.schemas import (
    AvatarEmotion,
    AvatarHint,
    AvatarState,
    ChatResponse,
)

__all__ = [
    "AvatarState",
    "AvatarEmotion",
    "AvatarHint",
    "AudioMetadata",
    "AvatarContractResponse",
    "AVATAR_STATES",
    "AVATAR_EMOTIONS",
    "AVATAR_CONTRACT_EXAMPLE",
    "to_avatar_contract",
]

# Controlled, backend-authoritative vocabulary (Section 15). The frontend may
# animate freely, but must only ever receive these exact values.
AVATAR_STATES: List[str] = [s.value for s in AvatarState]
AVATAR_EMOTIONS: List[str] = [e.value for e in AvatarEmotion]


class AudioMetadata(BaseModel):
    """Optional audio metadata, e.g. a pre-signed TTS URL.

    Always null in V1: the backend adds no paid avatar/voice provider. The field
    is reserved so a future integration can attach playable audio. It carries no
    authorization meaning.
    """

    model_config = ConfigDict(extra="ignore")

    url: Optional[str] = None
    duration: Optional[float] = None


class AvatarContractResponse(BaseModel):
    """Canonical backend -> frontend avatar contract (Section 15).

    The visual avatar is frontend-owned. The backend only supplies metadata the
    frontend uses to drive blinking, mouth, head, speaking state, and emotion.
    """

    model_config = ConfigDict(extra="ignore")

    conversation_id: str
    message_id: str
    text: str
    language: str
    persona: str
    avatar: AvatarHint
    audio: AudioMetadata = AudioMetadata()


# Matches the Section 15 example response exactly (audio null in V1).
AVATAR_CONTRACT_EXAMPLE: Dict[str, object] = {
    "conversation_id": "conv_001",
    "message_id": "msg_001",
    "text": "Rahul currently has 91.2% attendance.",
    "language": "en-IN",
    "persona": "parent",
    "avatar": {"state": "speaking", "emotion": "friendly"},
    "audio": {"url": None, "duration": None},
}


def to_avatar_contract(
    chat: ChatResponse,
    audio: Optional[AudioMetadata] = None,
) -> AvatarContractResponse:
    """Convert an orchestrator ChatResponse into the avatar contract shape."""
    return AvatarContractResponse(
        conversation_id=chat.conversation_id,
        message_id=chat.message_id,
        text=chat.text,
        language=chat.language,
        persona=chat.persona,
        avatar=chat.avatar,
        audio=audio or AudioMetadata(),
    )
