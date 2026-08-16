import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.cohere.models import LLMResponse
from app.providers.cohere.provider import set_llm_provider
from app.schemas.collections import AttendanceRecord
from app.schemas.user import Role
from app.services import attendance_service as att_svc
from app.services import conversation_service as conv_svc
from tests.test_ai_orchestrator import (
    STUDENTS,
    FakeAttendanceRepo,
    FakeConversationRepo,
    FakeMessageRepo,
    FakeStudentRepo,
    ScriptedProvider,
    ctx,
)


def decision(payload: dict) -> LLMResponse:
    return LLMResponse(text=json.dumps(payload), finish_reason="STOP")


@pytest.fixture
def api():
    conv_repo = FakeConversationRepo()
    msg_repos = {}
    conv_svc.set_conversation_repository(conv_repo)
    conv_svc.set_message_repository_factory(
        lambda cid: msg_repos.setdefault(cid, FakeMessageRepo())
    )
    att_svc.set_attendance_repository(
        FakeAttendanceRepo(
            [
                AttendanceRecord(id="a1", student_id="s1", class_id="c1",
                                 date="2026-08-10", status="PRESENT"),
            ]
        )
    )
    att_svc.set_student_repository(FakeStudentRepo(STUDENTS))

    app = create_app()

    contexts = {
        "PARENT": ctx(Role.PARENT, "p1", child_ids=["s1"]),
        "STUDENT": ctx(Role.STUDENT, "s1", student_id="s1", class_id="c1"),
        "INACTIVE": ctx(Role.STUDENT, "s1", active=False, student_id="s1"),
    }

    from app.api.v1 import ai as ai_module

    def use(role):
        async def _dep():
            return contexts[role]

        app.dependency_overrides[ai_module.get_auth_context] = _dep

    use("PARENT")

    # `with` runs the lifespan so built-in tools are registered.
    with TestClient(app) as client:
        yield client, use, msg_repos

    app.dependency_overrides.clear()
    set_llm_provider(None)
    conv_svc.set_conversation_repository(None)
    conv_svc.set_message_repository_factory(None)
    att_svc.set_attendance_repository(None)
    att_svc.set_student_repository(None)


def test_chat_returns_structured_response(api):
    client, use, _ = api
    set_llm_provider(
        ScriptedProvider(
            [
                decision(
                    {
                        "intent": "VIEW_CHILD_ATTENDANCE",
                        "entities": {"student_name": "Rahul"},
                        "tool_calls": [
                            {"name": "get_child_attendance",
                             "arguments": {"student_id": "s1"}}
                        ],
                    }
                ),
                LLMResponse(text="Rahul was present on 10 Aug.",
                            finish_reason="STOP"),
            ]
        )
    )

    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "How much attendance does my child have?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    data = body["data"]
    assert set(data) == {
        "conversation_id",
        "message_id",
        "text",
        "language",
        "persona",
        "tool_calls",
        "avatar",
    }
    assert data["text"] == "Rahul was present on 10 Aug."
    assert data["language"] == "en-IN"
    assert data["persona"] == "parent"
    assert data["avatar"] == {"state": "speaking", "emotion": "friendly"}
    assert data["tool_calls"] == [
        {"name": "get_child_attendance", "status": "OK", "message": None}
    ]


def test_chat_continues_existing_conversation(api):
    client, use, _ = api
    set_llm_provider(
        ScriptedProvider(
            [
                decision({"intent": "GENERAL_QUERY", "response_text": "Hello!"}),
                decision({"intent": "GENERAL_QUERY", "response_text": "Sure."}),
            ]
        )
    )

    first = client.post("/api/v1/ai/chat", json={"message": "Hi"}).json()["data"]
    second = client.post(
        "/api/v1/ai/chat",
        json={"conversation_id": first["conversation_id"], "message": "Thanks"},
    ).json()["data"]

    assert second["conversation_id"] == first["conversation_id"]
    assert second["message_id"] != first["message_id"]


def test_chat_rejects_empty_message(api):
    client, use, _ = api
    response = client.post("/api/v1/ai/chat", json={"message": ""})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_chat_rejects_oversized_message(api):
    client, use, _ = api
    response = client.post("/api/v1/ai/chat", json={"message": "x" * 5000})
    assert response.status_code == 422


def test_chat_rejects_inactive_user(api):
    client, use, _ = api
    use("INACTIVE")
    set_llm_provider(ScriptedProvider([]))
    response = client.post("/api/v1/ai/chat", json={"message": "Hi"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_chat_requires_authentication():
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/ai/chat", json={"message": "Hi"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_chat_ignores_client_supplied_role(api):
    client, use, msg_repos = api
    use("STUDENT")
    set_llm_provider(
        ScriptedProvider(
            [decision({"intent": "GENERAL_QUERY", "response_text": "Hello!"})]
        )
    )

    data = client.post(
        "/api/v1/ai/chat",
        json={"message": "Hi", "role": "PRINCIPAL", "user_id": "pr1"},
    ).json()["data"]

    # The extra fields are ignored; persona still comes from the stored role.
    assert data["persona"] == "student"
