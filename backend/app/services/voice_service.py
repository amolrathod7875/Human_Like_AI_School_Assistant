from typing import Any, Optional

from app.ai.orchestrator.orchestrator import handle_message
from app.ai.orchestrator.schemas import ChatRequest
from app.auth.authorization.context import AuthorizationContext
from app.core.config import settings
from app.core.errors import AppError


async def handle_voice_turn(
    context: AuthorizationContext,
    *,
    transcript: Optional[str],
    conversation_id: Optional[str] = None,
    language: Optional[str] = None,
    provider: Any = None,
) -> Any:
    """Run one spoken turn through the SAME orchestrator as chat.

    Voice and chat converge here: the exact same authorization context, tool
    registry, authorization engine, and persona pipeline are used. The only
    difference is the input channel — a transcript instead of a typed message.

    The transcript is treated as untrusted user input: it is length-bounded and
    validated exactly like the chat message; identity/role never come from it.
    """
    text = (transcript or "").strip()
    if not text:
        raise AppError("Empty voice transcript", "INVALID_EVENT", status_code=422)
    if len(text) > settings.AI_CONTEXT_MESSAGE_LIMIT * 400:
        # Generous hard cap; the orchestrator's own schema enforces the real one.
        text = text[:4000]

    request = ChatRequest(
        conversation_id=conversation_id,
        message=text,
        language=language,
    )
    return await handle_message(context, request, provider=provider)
