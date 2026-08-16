from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel

from app.ai.orchestrator.intents import Intent, tools_for_role
from app.ai.orchestrator.prompt import (
    build_decision_instructions,
    build_history,
    build_response_instructions,
    build_user_context,
)
from app.ai.orchestrator.schemas import (
    AvatarEmotion,
    AvatarHint,
    AvatarState,
    ChatRequest,
    ChatResponse,
    ModelDecision,
    ProposedToolCall,
    ToolCallStatus,
    ToolExecution,
)
from app.ai.orchestrator.validation import final_text, parse_decision
from app.ai.persona.language import get_language_instruction, normalize_language
from app.ai.persona.persona import get_persona
from app.ai.tools.errors import (
    InvalidArgumentsError,
    ToolAuthorizationError,
    ToolError,
    ToolNotFoundError,
    ToolResultValidationError,
)
from app.ai.tools.registry import execute_tool, get_tool, list_tool_definitions
from app.auth.authorization.context import AuthorizationContext
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.providers.cohere.errors import LLMProviderError
from app.providers.cohere.models import (
    LLMMessage,
    LLMRequest,
    LLMToolDefinition,
)
from app.providers.cohere.provider import get_llm_provider
from app.schemas.collections import Conversation, Message
from app.schemas.user import Role
from app.services.conversation_service import (
    append_message,
    build_context,
    create_conversation,
    get_conversation,
)

logger = get_logger("app.ai.orchestrator")

DEFAULT_LANGUAGE_TAG = "en-IN"

# Largest tool result list forwarded to the model (context/cost guard).
_MAX_RESULT_ITEMS = 50

# User-facing messages. Deliberately generic: they never expose internal rules,
# other users' data, tool names, or error internals.
MSG_DENIED = "You do not have access to that."
MSG_CLARIFY = "More details are needed before this can be done."
MSG_UNAVAILABLE = "That capability is not available yet."
MSG_ERROR = "That request could not be completed."
MSG_BUSY = (
    "I am unable to answer right now. Please try again in a moment."
)
MSG_DEFAULT = "I can help with attendance and school information."


async def handle_message(
    context: AuthorizationContext,
    request: ChatRequest,
    *,
    provider: Any = None,
) -> ChatResponse:
    """Run the full natural-language turn for an authenticated caller.

    Flow: authenticated context -> conversation/language/persona -> LLM intent
    decision -> validate output -> registry tool call (authorization + execute)
    -> LLM final response -> persist messages -> structured response.

    The orchestrator is NOT the authorization engine: every tool call goes
    through `app.ai.tools.registry.execute_tool`, which validates arguments and
    applies the Section 05 policies. A model-requested action that is refused
    there stays refused here.
    """
    if not context.active:
        raise AppError("User is not active", "FORBIDDEN", status_code=403)

    conversation = _load_conversation(context, request)
    conversation_id = conversation.id or ""
    conv_context = build_context(
        conversation_id, context, limit=settings.AI_CONTEXT_MESSAGE_LIMIT
    )

    language_tag = conversation.language or DEFAULT_LANGUAGE_TAG
    language_code = normalize_language(language_tag)
    persona = get_persona(context.role)
    llm = provider or get_llm_provider()

    decision = await _decide(
        llm,
        context=context,
        request=request,
        conv_context=conv_context,
        persona=persona,
        language_tag=language_tag,
        language_code=language_code,
        conversation_id=conversation_id,
    )

    degraded = decision is None
    if decision is None:
        decision = ModelDecision(intent=Intent.GENERAL_QUERY)

    executions = await _execute_tools(context, decision)

    if degraded:
        text = MSG_BUSY
    elif executions:
        text = await _respond(
            llm,
            context=context,
            request=request,
            decision=decision,
            executions=executions,
            conv_context=conv_context,
            persona=persona,
            language_tag=language_tag,
            language_code=language_code,
            conversation_id=conversation_id,
        )
    else:
        text = (
            decision.clarification_question
            or decision.response_text
            or MSG_DEFAULT
        )

    message_id = _persist(
        context,
        conversation_id=conversation_id,
        request=request,
        decision=decision,
        executions=executions,
        text=text,
    )

    return ChatResponse(
        conversation_id=conversation_id,
        message_id=message_id,
        text=text,
        language=language_tag,
        persona=context.role.value.lower(),
        tool_calls=[execution.to_record() for execution in executions],
        avatar=_avatar_hint(context.role, decision, executions, degraded),
    )


# ---------------------------------------------------------------- conversation
def _load_conversation(
    context: AuthorizationContext, request: ChatRequest
) -> Conversation:
    """Load the caller's conversation, or start a new one.

    Ownership is enforced by the conversation engine, so a caller can never
    continue somebody else's conversation.
    """
    if request.conversation_id:
        return get_conversation(request.conversation_id, context)
    return create_conversation(
        context, language=request.language or DEFAULT_LANGUAGE_TAG
    )


# ------------------------------------------------------------------- decision
def _tool_definitions(role: Role) -> List[LLMToolDefinition]:
    """Registered tool definitions, narrowed to those relevant for the role."""
    definitions = list_tool_definitions()
    allowed = set(tools_for_role(role, [d["name"] for d in definitions]))
    return [
        LLMToolDefinition(
            name=d["name"],
            description=d["description"],
            parameters=d.get("parameters") or {},
        )
        for d in definitions
        if d["name"] in allowed
    ]


def _messages(conv_context, user_message: str) -> List[LLMMessage]:
    history = build_history(
        conv_context.recent_messages, limit=settings.AI_CONTEXT_MESSAGE_LIMIT
    )
    return [LLMMessage(role=h["role"], content=h["content"]) for h in history] + [
        LLMMessage(role="user", content=user_message)
    ]


async def _decide(
    llm: Any,
    *,
    context: AuthorizationContext,
    request: ChatRequest,
    conv_context,
    persona,
    language_tag: str,
    language_code: str,
    conversation_id: str,
) -> Optional[ModelDecision]:
    """First pass: intent, entities, and any requested tool calls.

    Returns `None` when the provider is unavailable so the caller can degrade
    gracefully instead of guessing an answer.
    """
    definitions = _tool_definitions(context.role)
    llm_request = LLMRequest(
        messages=_messages(conv_context, request.message),
        system_instructions=build_decision_instructions(
            context.role, [d.name for d in definitions]
        ),
        user_context=build_user_context(
            context=context,
            persona=persona,
            language_tag=language_tag,
            conversation_id=conversation_id,
            known_entities=conv_context.known_entities,
            previous_results=_limit(conv_context.previous_tool_results),
            today=datetime.now(timezone.utc).date().isoformat(),
        ),
        tool_definitions=definitions or None,
        persona_instruction=persona.instruction,
        language_instruction=get_language_instruction(language_code),
    )

    try:
        response = await llm.generate(llm_request)
    except LLMProviderError as exc:
        # Never log the request payload or provider credentials.
        logger.warning("LLM decision call failed: %s", exc.__class__.__name__)
        return None

    decision = parse_decision(
        response, max_tool_calls=settings.AI_MAX_TOOL_CALLS
    )
    logger.info(
        "AI decision role=%s intent=%s tools=%s",
        context.role.value,
        decision.intent.value,
        [call.name for call in decision.tool_calls],
    )
    return decision


# ------------------------------------------------------------- tool execution
async def _execute_tools(
    context: AuthorizationContext, decision: ModelDecision
) -> List[ToolExecution]:
    executions: List[ToolExecution] = []
    for call in decision.tool_calls:
        executions.append(await _execute_one(context, call))
    return executions


async def _execute_one(
    context: AuthorizationContext, call: ProposedToolCall
) -> ToolExecution:
    """Run one model-requested tool through the registry pipeline.

    Failures are mapped to sanitized statuses/messages; provider-facing and
    user-facing text never contains raw error details.
    """

    def outcome(status: ToolCallStatus, message: Optional[str] = None, result=None):
        return ToolExecution(
            name=call.name,
            arguments=call.arguments,
            status=status,
            message=message,
            result=result,
        )

    # Allowlist check first: an unregistered name is never executed.
    if get_tool(call.name) is None:
        logger.warning("TOOL_REJECTED unregistered tool requested: %s", call.name)
        return outcome(ToolCallStatus.UNAVAILABLE, MSG_UNAVAILABLE)

    try:
        result = await execute_tool(call.name, context, call.arguments)
    except ToolAuthorizationError:
        logger.warning(
            "AUTHORIZATION_DENIED tool=%s role=%s", call.name, context.role.value
        )
        return outcome(ToolCallStatus.DENIED, MSG_DENIED)
    except InvalidArgumentsError:
        # Ambiguous or incomplete reference: ask, never guess.
        logger.info("TOOL_REJECTED invalid arguments tool=%s", call.name)
        return outcome(ToolCallStatus.NEEDS_CLARIFICATION, MSG_CLARIFY)
    except ToolNotFoundError:
        logger.warning("TOOL_REJECTED unknown tool=%s", call.name)
        return outcome(ToolCallStatus.UNAVAILABLE, MSG_UNAVAILABLE)
    except ToolResultValidationError:
        logger.error("Tool result validation failed tool=%s", call.name)
        return outcome(ToolCallStatus.ERROR, MSG_ERROR)
    except ToolError:
        logger.error("Tool execution failed tool=%s", call.name)
        return outcome(ToolCallStatus.ERROR, MSG_ERROR)
    except AppError as exc:
        # e.g. a policy `enforce()` raised during a tool's authorize phase.
        if exc.status_code == 403:
            logger.warning(
                "AUTHORIZATION_DENIED tool=%s role=%s", call.name, context.role.value
            )
            return outcome(ToolCallStatus.DENIED, MSG_DENIED)
        logger.error("Tool failed tool=%s code=%s", call.name, exc.code)
        return outcome(ToolCallStatus.ERROR, MSG_ERROR)
    except Exception:  # pragma: no cover - defensive
        logger.exception("Unexpected tool failure tool=%s", call.name)
        return outcome(ToolCallStatus.ERROR, MSG_ERROR)

    return outcome(ToolCallStatus.OK, result=_jsonable(result))


# --------------------------------------------------------------- final answer
async def _respond(
    llm: Any,
    *,
    context: AuthorizationContext,
    request: ChatRequest,
    decision: ModelDecision,
    executions: Sequence[ToolExecution],
    conv_context,
    persona,
    language_tag: str,
    language_code: str,
    conversation_id: str,
) -> str:
    """Second pass: turn validated tool results into natural language."""
    llm_request = LLMRequest(
        messages=_messages(conv_context, request.message),
        system_instructions=build_response_instructions(context.role),
        user_context=build_user_context(
            context=context,
            persona=persona,
            language_tag=language_tag,
            conversation_id=conversation_id,
            known_entities={**conv_context.known_entities, **decision.entities},
            tool_results=_tool_payload(executions),
            today=datetime.now(timezone.utc).date().isoformat(),
        ),
        persona_instruction=persona.instruction,
        language_instruction=get_language_instruction(language_code),
    )

    try:
        response = await llm.generate(llm_request)
    except LLMProviderError as exc:
        logger.warning("LLM response call failed: %s", exc.__class__.__name__)
        return _fallback_text(executions)

    return final_text(response) or _fallback_text(executions)


def _fallback_text(executions: Sequence[ToolExecution]) -> str:
    """Deterministic wording used when the model cannot phrase the answer.

    It never claims that an action succeeded.
    """
    statuses = {execution.status for execution in executions}
    if ToolCallStatus.DENIED in statuses:
        return MSG_DENIED
    if ToolCallStatus.NEEDS_CLARIFICATION in statuses:
        return MSG_CLARIFY
    if ToolCallStatus.UNAVAILABLE in statuses:
        return MSG_UNAVAILABLE
    if ToolCallStatus.ERROR in statuses:
        return MSG_ERROR
    return MSG_BUSY


def _tool_payload(executions: Sequence[ToolExecution]) -> List[Dict[str, Any]]:
    """Validated, sanitized tool outcomes for the generation context."""
    payload: List[Dict[str, Any]] = []
    for execution in executions:
        entry: Dict[str, Any] = {
            "tool": execution.name,
            "status": execution.status.value,
        }
        if execution.status == ToolCallStatus.OK:
            entry["result"] = _limit(execution.result)
        elif execution.message:
            entry["message"] = execution.message
        payload.append(entry)
    return payload


# ------------------------------------------------------------------ persistence
def _persist(
    context: AuthorizationContext,
    *,
    conversation_id: str,
    request: ChatRequest,
    decision: ModelDecision,
    executions: Sequence[ToolExecution],
    text: str,
) -> str:
    """Store the user turn, any tool activity, and the assistant reply."""
    now = datetime.now(timezone.utc)

    append_message(
        conversation_id,
        Message(
            role="user",
            content=request.message,
            intent=decision.intent.value,
            entities=decision.entities,
            timestamp=now,
        ),
        context,
    )

    if executions:
        append_message(
            conversation_id,
            Message(
                role="tool",
                content="",
                intent=decision.intent.value,
                tool_calls=[
                    {"name": e.name, "arguments": _jsonable(e.arguments)}
                    for e in executions
                ],
                tool_results=[
                    {
                        "name": e.name,
                        "status": e.status.value,
                        "message": e.message,
                        "result": _limit(e.result),
                    }
                    for e in executions
                ],
                timestamp=now + timedelta(milliseconds=1),
            ),
            context,
        )

    saved = append_message(
        conversation_id,
        Message(
            role="assistant",
            content=text,
            intent=decision.intent.value,
            timestamp=now + timedelta(milliseconds=2),
        ),
        context,
    )
    return saved.id or ""


# ----------------------------------------------------------------- avatar hint
def _avatar_hint(
    role: Role,
    decision: ModelDecision,
    executions: Sequence[ToolExecution],
    degraded: bool,
) -> AvatarHint:
    """Presentation hint for the frontend avatar (no authorization meaning)."""
    statuses = {execution.status for execution in executions}

    if degraded or statuses & {
        ToolCallStatus.DENIED,
        ToolCallStatus.ERROR,
        ToolCallStatus.UNAVAILABLE,
    }:
        emotion = AvatarEmotion.CONCERNED
    elif (
        ToolCallStatus.NEEDS_CLARIFICATION in statuses
        or decision.missing_information
        or decision.clarification_question
    ):
        emotion = AvatarEmotion.NEUTRAL
    elif role in (Role.STUDENT, Role.PARENT):
        emotion = AvatarEmotion.FRIENDLY
    else:
        emotion = AvatarEmotion.PROFESSIONAL

    return AvatarHint(state=AvatarState.SPEAKING, emotion=emotion)


# ---------------------------------------------------------------------- helpers
def _jsonable(value: Any) -> Any:
    """Convert Pydantic models / nested containers to JSON-safe values."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _limit(value: Any, max_items: int = _MAX_RESULT_ITEMS) -> Any:
    """Bound list payloads handed to the model or stored for audit."""
    value = _jsonable(value)
    if isinstance(value, list) and len(value) > max_items:
        return {
            "items": value[:max_items],
            "total_items": len(value),
            "truncated": True,
        }
    return value
