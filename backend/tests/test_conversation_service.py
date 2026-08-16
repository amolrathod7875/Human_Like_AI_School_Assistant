import pytest
from datetime import datetime, timezone

from app.auth.authorization.context import build_authorization_context
from app.core.errors import AppError
from app.repositories.base import Page
from app.schemas.collections import Conversation, Message
from app.schemas.user import Role, UserProfile
from app.services import conversation_service as svc


class FakeConversationRepo:
    def __init__(self):
        self.store = {}

    def create(self, model):
        mid = model.id or f"conv_{len(self.store) + 1}"
        created = model.model_copy(update={"id": mid})
        self.store[mid] = created
        return created

    def get(self, doc_id):
        return self.store.get(doc_id)


class FakeMessageRepo:
    def __init__(self):
        self.store = []

    def create(self, model):
        mid = model.id or f"msg_{len(self.store) + 1}"
        created = model.model_copy(update={"id": mid})
        self.store.append(created)
        return created

    def list(self, *, filters=None, order_by=None, desc=False, page_size=20, start_after=None):
        items = list(self.store)
        if order_by == "timestamp":
            items.sort(key=lambda m: m.timestamp or datetime.min, reverse=desc)
        return Page(items=items[:page_size])


@pytest.fixture
def setup():
    conv_repo = FakeConversationRepo()
    msg_repos = {}
    svc.set_conversation_repository(conv_repo)
    svc.set_message_repository_factory(
        lambda cid: msg_repos.setdefault(cid, FakeMessageRepo())
    )
    yield conv_repo, msg_repos
    svc.set_conversation_repository(None)
    svc.set_message_repository_factory(None)


def student_ctx(uid="uA"):
    return build_authorization_context(
        UserProfile(
            id=uid, firebase_uid=f"fb_{uid}", name="S", role=Role.STUDENT,
            student_id=uid,
        )
    )


def parent_ctx(uid="uP"):
    return build_authorization_context(
        UserProfile(
            id=uid, firebase_uid=f"fb_{uid}", name="P", role=Role.PARENT,
            child_ids=["c1"],
        )
    )


def principal_ctx(uid="uPR"):
    return build_authorization_context(
        UserProfile(id=uid, firebase_uid=f"fb_{uid}", name="PR", role=Role.PRINCIPAL)
    )


def test_create_conversation(setup):
    ctx = student_ctx()
    conv = svc.create_conversation(ctx, language="en-IN")
    assert conv.user_id == "uA"
    assert conv.role == "STUDENT"
    assert conv.language == "en-IN"
    assert conv.id


def test_append_and_recent_messages(setup):
    ctx = student_ctx()
    conv = svc.create_conversation(ctx)
    svc.append_message(
        conv.id,
        Message(role="user", content="hi", timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        ctx,
    )
    svc.append_message(
        conv.id,
        Message(role="assistant", content="hello", timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc)),
        ctx,
    )
    recent = svc.get_recent_messages(conv.id, ctx, limit=10)
    assert len(recent) == 2
    assert recent[0].content == "hello"  # most recent first


def test_ownership_enforcement(setup):
    owner = student_ctx("uA")
    intruder = student_ctx("uB")
    conv = svc.create_conversation(owner)

    with pytest.raises(AppError) as exc:
        svc.get_conversation(conv.id, intruder)
    assert exc.value.code == "FORBIDDEN"

    # Owner can access their own conversation.
    assert svc.get_conversation(conv.id, owner).id == conv.id


def test_append_by_intruder_forbidden(setup):
    owner = student_ctx("uA")
    intruder = student_ctx("uB")
    conv = svc.create_conversation(owner)
    with pytest.raises(AppError):
        svc.append_message(
            conv.id,
            Message(role="user", content="x", timestamp=datetime.now(timezone.utc)),
            intruder,
        )


def test_principal_can_access_others(setup):
    owner = student_ctx("uA")
    principal = principal_ctx()
    conv = svc.create_conversation(owner)
    assert svc.get_conversation(conv.id, principal).id == conv.id


def test_context_generation_and_follow_up(setup):
    ctx = parent_ctx("uP")
    conv = svc.create_conversation(ctx, language="en-IN")

    svc.append_message(
        conv.id,
        Message(
            role="user",
            content="How much attendance does Rahul have?",
            intent="VIEW_CHILD_ATTENDANCE",
            entities={"student_name": "Rahul"},
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        ctx,
    )
    svc.append_message(
        conv.id,
        Message(
            role="tool",
            content="",
            tool_results=[{"attendance": 91.2}],
            timestamp=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
        ),
        ctx,
    )
    svc.append_message(
        conv.id,
        Message(
            role="user",
            content="What about last month?",
            timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ),
        ctx,
    )

    ctxt = svc.build_context(conv.id, ctx, limit=20)
    assert ctxt.language == "en-IN"
    # Follow-up can rely on context from earlier messages.
    assert ctxt.known_entities.get("student_name") == "Rahul"
    assert any(
        isinstance(r, dict) and r.get("attendance") == 91.2 for r in ctxt.previous_tool_results
    )
    # Most recent message first.
    assert ctxt.recent_messages[0].content == "What about last month?"
