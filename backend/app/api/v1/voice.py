import types
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request

from app.ai.orchestrator.schemas import ChatResponse
from app.auth.authorization.context import (
    AuthorizationContext,
    get_authorization_context,
)
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_authenticated_user
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.responses import ApiResponse, success_response
from app.providers.vapi import (
    VapiAdapter,
    VapiError,
    VapiWebhookError,
    get_vapi_adapter,
    get_voice_session_store,
    safe_message,
    to_app_error,
)
from app.providers.vapi.verifier import VAPI_SIGNATURE_HEADER
from app.schemas.voice import VoiceReply, VoiceTurnRequest
from app.security import SUSPICIOUS_INPUT, log_security_event
from app.services.voice_service import handle_voice_turn

logger = get_logger("app.api.v1.voice")

router = APIRouter(prefix="/voice", tags=["voice"])


# Reusable dependency so tests / other coders can swap the adapter.
def get_voice_adapter() -> VapiAdapter:
    return get_vapi_adapter()


async def get_voice_auth_context(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> AuthorizationContext:
    """Resolve the caller's authorization context from a verified bearer token.

    Uses the EXACT same resolution as chat — voice is not a separate auth path.
    """
    return get_authorization_context(user)


def _vapi_safe_reply(adapter: VapiAdapter, event: Any, kind: str) -> dict:
    """Build a Vapi `results` payload with a safe, non-revealing spoken text."""
    fake = types.SimpleNamespace(text=safe_message(kind))
    return adapter.respond(event, fake)


def _conversation_id_for(event: Any, session: Any) -> Optional[str]:
    """Resolve the conversation id to pass to the orchestrator.

    Prefers an explicit id from trusted call metadata, then a previously
    recorded call→conversation mapping. Returns None when the turn should start
    a brand-new conversation (the orchestrator creates and returns its id).
    """
    if event.conversation_id:
        return event.conversation_id
    if event.call_id:
        return session.get(event.call_id)
    return None


@router.post("/webhook")
async def voice_webhook(
    request: Request,
    adapter: VapiAdapter = Depends(get_voice_adapter),
) -> Any:
    """Vapi server-URL endpoint.

    Vapi authenticates the request via an HMAC signature; the caller's identity
    is taken from the call's server-side metadata (never the transcript). The
    turn is then run through the SAME orchestrator as chat — no separate
    authorization path is created. Returns Vapi's expected `results` shape so
    Vapi can speak the reply.
    """
    raw_body = await request.body()
    signature = request.headers.get(VAPI_SIGNATURE_HEADER)

    try:
        event = adapter.parse(raw_body, signature)
    except VapiWebhookError as exc:
        raise to_app_error(exc)
    except VapiError as exc:
        raise to_app_error(exc)

    # Informational events (transcripts, status updates, end-of-call) need no
    # reply. Acknowledge so Vapi does not retry.
    if not event.requires_reply:
        return {"received": True, "event": event.event_type}

    # Identity must come from trusted call metadata, not the spoken words.
    if not event.firebase_uid:
        log_security_event(
            SUSPICIOUS_INPUT,
            f"voice webhook missing identity call_id={event.call_id}",
        )
        return _vapi_safe_reply(adapter, event, "account_unidentified")

    try:
        context = get_authorization_context(
            AuthenticatedUser(firebase_uid=event.firebase_uid)
        )
    except AppError:
        return _vapi_safe_reply(adapter, event, "account_error")

    session = get_voice_session_store()
    conversation_id = _conversation_id_for(event, session)

    try:
        response = await handle_voice_turn(
            context,
            transcript=event.transcript,
            conversation_id=conversation_id,
            language=event.language,
        )
    except AppError as exc:
        if conversation_id is not None and exc.code == "NOT_FOUND":
            # A supplied id did not exist yet; let the orchestrator create one.
            try:
                response = await handle_voice_turn(
                    context,
                    transcript=event.transcript,
                    conversation_id=None,
                    language=event.language,
                )
            except AppError as inner:
                logger.warning("VOICE_TURN_FAILED code=%s", inner.code)
                return _vapi_safe_reply(adapter, event, "unavailable")
        else:
            # Never expose internal errors to the caller on a live call.
            logger.warning("VOICE_TURN_FAILED code=%s", exc.code)
            return _vapi_safe_reply(adapter, event, "unavailable")

    # Record the mapping so later turns in the same call reuse the conversation.
    if event.call_id and not event.conversation_id:
        session.set(event.call_id, response.conversation_id)

    return adapter.respond(event, response)


@router.post("/respond", response_model=ApiResponse[VoiceReply])
async def voice_respond(
    payload: VoiceTurnRequest,
    context: AuthorizationContext = Depends(get_voice_auth_context),
) -> ApiResponse[VoiceReply]:
    """Bearer-authenticated voice turn (converges into the orchestrator).

    Same authorization and tool pipeline as `POST /ai/chat`, but accepts a
    transcript and returns a TTS-ready `say` field alongside the structured
    response.
    """
    response: ChatResponse = await handle_voice_turn(
        context,
        transcript=payload.transcript,
        conversation_id=payload.conversation_id,
        language=payload.language,
    )
    return success_response(
        VoiceReply(
            conversation_id=response.conversation_id,
            text=response.text,
            say=response.text,
            language=response.language,
            persona=response.persona,
            tool_calls=response.tool_calls,
            avatar=response.avatar,
        )
    )
