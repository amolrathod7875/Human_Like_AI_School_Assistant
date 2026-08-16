from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.ai.orchestrator.intents import Intent

# Hard cap on a single user turn. Long payloads are a common injection vector
# and cost driver, so they are rejected at the schema boundary (422).
MAX_MESSAGE_LENGTH = 4000


class AvatarState(str, Enum):
    """Frontend avatar states (Section 15 contract, lowercase on the wire)."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class AvatarEmotion(str, Enum):
    """Small, controlled emotion vocabulary suggested to the frontend."""

    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    CONCERNED = "concerned"
    HAPPY = "happy"
    PROFESSIONAL = "professional"


class AvatarHint(BaseModel):
    """Presentation-only hint. Carries no authorization meaning."""

    model_config = ConfigDict(extra="ignore")

    state: AvatarState = AvatarState.SPEAKING
    emotion: AvatarEmotion = AvatarEmotion.NEUTRAL


class ToolCallStatus(str, Enum):
    """Outcome of one tool call, after registry validation + authorization."""

    OK = "OK"
    DENIED = "DENIED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class ToolCallRecord(BaseModel):
    """Sanitized tool-call summary returned to the client.

    Arguments and raw results are deliberately NOT exposed here; they are kept
    server-side (conversation history) for audit.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    status: ToolCallStatus
    message: Optional[str] = None


class ChatRequest(BaseModel):
    """Orchestrator input. Identity/role never come from the client."""

    model_config = ConfigDict(extra="ignore")

    conversation_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    # Optional language hint, applied only when a NEW conversation is created.
    # It affects phrasing only, never authorization.
    language: Optional[str] = None


class ChatResponse(BaseModel):
    """Structured orchestrator response (Section 11 / Section 15 contract)."""

    model_config = ConfigDict(extra="ignore")

    conversation_id: str
    message_id: str
    text: str
    language: str
    persona: str
    tool_calls: List[ToolCallRecord] = []
    avatar: AvatarHint = AvatarHint()


class ProposedToolCall(BaseModel):
    """A tool call *requested* by the model (never trusted as authorized)."""

    model_config = ConfigDict(extra="ignore")

    name: str
    arguments: Dict[str, Any] = {}


class ModelDecision(BaseModel):
    """Validated interpretation of the model's first-pass output."""

    model_config = ConfigDict(extra="ignore")

    intent: Intent = Intent.GENERAL_QUERY
    entities: Dict[str, Any] = {}
    tool_calls: List[ProposedToolCall] = []
    missing_information: List[str] = []
    clarification_question: Optional[str] = None
    response_text: Optional[str] = None


class ToolExecution(BaseModel):
    """Server-side record of one executed (or refused) tool call."""

    model_config = ConfigDict(extra="ignore")

    name: str
    arguments: Dict[str, Any] = {}
    status: ToolCallStatus
    message: Optional[str] = None
    result: Optional[Any] = None

    def to_record(self) -> ToolCallRecord:
        return ToolCallRecord(
            name=self.name, status=self.status, message=self.message
        )
