from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.auth.authorization.context import AuthorizationContext
from app.core.errors import AppError
from app.repositories import ConversationRepository
from app.repositories.firestore.message import MessageRepository
from app.schemas.collections import Conversation, Message

# Dependency injection points (overridden by tests).
_conversation_repo: Optional[ConversationRepository] = None
_message_repo_factory = None


def set_conversation_repository(repo: Optional[ConversationRepository]) -> None:
    global _conversation_repo
    _conversation_repo = repo


def get_conversation_repository() -> ConversationRepository:
    global _conversation_repo
    if _conversation_repo is None:
        _conversation_repo = ConversationRepository()
    return _conversation_repo


def set_message_repository_factory(factory) -> None:
    global _message_repo_factory
    _message_repo_factory = factory


def get_message_repository(conversation_id: str) -> MessageRepository:
    global _message_repo_factory
    if _message_repo_factory is None:
        return MessageRepository(conversation_id)
    return _message_repo_factory(conversation_id)


class ConversationContext(BaseModel):
    """Structured context handed to the AI orchestrator."""

    conversation_id: str
    recent_messages: List[Message]
    language: Optional[str]
    known_entities: Dict[str, Any]
    previous_tool_results: List[Any]


def _assert_owner(conv: Conversation, context: AuthorizationContext) -> None:
    # PRINCIPAL (school_wide) may access any conversation per administrative
    # policy; everyone else is restricted to conversations they own.
    if context.relationship.school_wide:
        return
    if conv.user_id != context.user_id:
        raise AppError(
            "Not authorized for this conversation", "FORBIDDEN", status_code=403
        )


def create_conversation(
    context: AuthorizationContext,
    language: str = "en-IN",
    metadata: Optional[Dict[str, Any]] = None,
) -> Conversation:
    # Role comes from the stored identity, never from the client.
    conv = Conversation(
        id="",
        user_id=context.user_id,
        role=context.role.value,
        language=language,
        metadata=metadata or {},
    )
    return get_conversation_repository().create(conv)


def get_conversation(conversation_id: str, context: AuthorizationContext) -> Conversation:
    conv = get_conversation_repository().get(conversation_id)
    if conv is None:
        raise AppError("Conversation not found", "NOT_FOUND", status_code=404)
    _assert_owner(conv, context)
    return conv


def append_message(
    conversation_id: str, message: Message, context: AuthorizationContext
) -> Message:
    # Ownership of the parent conversation is enforced before writing.
    get_conversation(conversation_id, context)
    if message.timestamp is None:
        message = message.model_copy(
            update={"timestamp": datetime.now(timezone.utc)}
        )
    return get_message_repository(conversation_id).create(message)


def get_recent_messages(
    conversation_id: str, context: AuthorizationContext, limit: int = 20
) -> List[Message]:
    get_conversation(conversation_id, context)
    page = get_message_repository(conversation_id).list(
        order_by="timestamp", desc=True, page_size=limit
    )
    return page.items


def build_context(
    conversation_id: str, context: AuthorizationContext, limit: int = 20
) -> ConversationContext:
    conv = get_conversation(conversation_id, context)
    messages = get_recent_messages(conversation_id, context, limit=limit)

    known_entities: Dict[str, Any] = {}
    previous_tool_results: List[Any] = []
    for message in messages:
        if message.entities:
            known_entities.update(message.entities)
        if message.tool_results:
            previous_tool_results.extend(message.tool_results)

    return ConversationContext(
        conversation_id=conv.id,
        recent_messages=messages,
        language=conv.language,
        known_entities=known_entities,
        previous_tool_results=previous_tool_results,
    )
