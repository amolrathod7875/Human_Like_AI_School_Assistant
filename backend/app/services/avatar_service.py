from typing import Dict, List, Optional

from app.ai.orchestrator.schemas import ChatResponse
from app.schemas.avatar import (
    AVATAR_CONTRACT_EXAMPLE,
    AVATAR_EMOTIONS,
    AVATAR_STATES,
    AudioMetadata,
    AvatarContractResponse,
    to_avatar_contract,
)

__all__ = ["build_avatar_contract", "get_avatar_contract_spec"]

# Field-level documentation surfaced to the frontend via GET /avatar/contract.
_CONTRACT_FIELDS: Dict[str, str] = {
    "conversation_id": "Opaque id linking this turn to a conversation.",
    "message_id": "Opaque id for this specific assistant message.",
    "text": "Spoken/displayed reply text.",
    "language": "BCP-47 language tag, e.g. en-IN.",
    "persona": "Caller persona (student/parent/teacher/principal).",
    "avatar.state": "One of the allowed avatar states.",
    "avatar.emotion": "One of the allowed emotions.",
    "audio.url": "Optional audio URL (null in V1).",
    "audio.duration": "Optional audio duration in seconds (null in V1).",
}


def build_avatar_contract(
    chat: ChatResponse,
    audio: Optional[AudioMetadata] = None,
) -> AvatarContractResponse:
    """Produce the avatar contract payload from an orchestrator turn."""
    return to_avatar_contract(chat, audio=audio)


def get_avatar_contract_spec() -> Dict[str, object]:
    """Static description of the avatar contract for frontend discovery."""
    return {
        "contract": "avatar",
        "description": (
            "Backend-supplied metadata the Lovable avatar uses to render state "
            "and emotion. The visual avatar is frontend-owned; the backend only "
            "suggests presentation and never adds a paid avatar provider."
        ),
        "states": AVATAR_STATES,
        "emotions": AVATAR_EMOTIONS,
        "fields": _CONTRACT_FIELDS,
        "example": AVATAR_CONTRACT_EXAMPLE,
        "rule": "No paid avatar provider is added to the backend.",
    }
