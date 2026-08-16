import json

import pytest
from fastapi.testclient import TestClient

from app.ai.orchestrator.orchestrator import handle_message
from app.ai.orchestrator.schemas import (
    AvatarEmotion,
    AvatarHint,
    AvatarState,
    ChatResponse,
)
from app.main import create_app
from app.providers.cohere.models import LLMResponse
from app.providers.cohere.provider import set_llm_provider
from app.schemas.avatar import (
    AVATAR_CONTRACT_EXAMPLE,
    AVATAR_EMOTIONS,
    AVATAR_STATES,
    AudioMetadata,
    AvatarContractResponse,
    to_avatar_contract,
)
from app.services.avatar_service import (
    build_avatar_contract,
    get_avatar_contract_spec,
)
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
from app.services import attendance_service as att_svc
from app.schemas.collections import AttendanceRecord
from app.schemas.user import Role


def decision(payload: dict) -> LLMResponse:
    return LLMResponse(text=json.dumps(payload), finish_reason="STOP")


# --------------------------------------------------------------------- unit
def test_avatar_vocabulary_is_controlled():
    assert set(AVATAR_STATES) == {"idle", "listening", "thinking", "speaking"}
    assert set(AVATAR_EMOTIONS) == {
        "friendly",
        "neutral",
        "concerned",
        "happy",
        "professional",
    }


def test_to_avatar_contract_maps_fields():
    chat = ChatResponse(
        conversation_id="conv_1",
        message_id="msg_1",
        text="Hi there.",
        language="en-IN",
        persona="parent",
        avatar=AvatarHint(state=AvatarState.SPEAKING, emotion=AvatarEmotion.FRIENDLY),
    )
    contract = to_avatar_contract(chat)
    assert isinstance(contract, AvatarContractResponse)
    assert contract.conversation_id == "conv_1"
    assert contract.message_id == "msg_1"
    assert contract.text == "Hi there."
    assert contract.language == "en-IN"
    assert contract.persona == "parent"
    assert contract.avatar.state == AvatarState.SPEAKING
    assert contract.avatar.emotion == AvatarEmotion.FRIENDLY
    # Audio is null by default in V1.
    assert contract.audio.url is None
    assert contract.audio.duration is None


def test_to_avatar_contract_accepts_audio():
    chat = ChatResponse(
        conversation_id="c",
        message_id="m",
        text="t",
        language="en-IN",
        persona="student",
    )
    audio = AudioMetadata(url="https://x/a.wav", duration=1.5)
    contract = to_avatar_contract(chat, audio=audio)
    assert contract.audio.url == "https://x/a.wav"
    assert contract.audio.duration == 1.5


def test_service_build_and_spec():
    chat = ChatResponse(
        conversation_id="c",
        message_id="m",
        text="t",
        language="hi-IN",
        persona="teacher",
    )
    contract = build_avatar_contract(chat)
    assert contract.language == "hi-IN"

    spec = get_avatar_contract_spec()
    assert spec["states"] == AVATAR_STATES
    assert spec["emotions"] == AVATAR_EMOTIONS
    assert spec["example"] == AVATAR_CONTRACT_EXAMPLE
    assert "No paid avatar provider" in spec["rule"]


# ---------------------------------------------------------------------- api
@pytest.fixture
def client():
    conv_repo = FakeConversationRepo()
    msg_repos = {}
    conv_svc.set_conversation_repository(conv_repo)
    conv_svc.set_message_repository_factory(
        lambda cid: msg_repos.setdefault(cid, FakeMessageRepo())
    )
    att_svc.set_attendance_repository(
        FakeAttendanceRepo(
            [
                AttendanceRecord(
                    id="a1", student_id="s1", class_id="c1",
                    date="2026-08-10", status="PRESENT",
                ),
            ]
        )
    )
    att_svc.set_student_repository(FakeStudentRepo(STUDENTS))

    app = create_app()

    contexts = {"PARENT": ctx(Role.PARENT, "p1", child_ids=["s1"])}
    from app.api.v1 import avatar as avatar_module

    def use(role):
        async def _dep():
            return contexts[role]

        app.dependency_overrides[avatar_module.get_auth_context] = _dep

    use("PARENT")

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    set_llm_provider(None)
    conv_svc.set_conversation_repository(None)
    conv_svc.set_message_repository_factory(None)
    att_svc.set_attendance_repository(None)
    att_svc.set_student_repository(None)


def test_get_contract_spec(client):
    response = client.get("/api/v1/avatar/contract")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["states"] == AVATAR_STATES
    assert data["emotions"] == AVATAR_EMOTIONS
    assert data["example"] == AVATAR_CONTRACT_EXAMPLE
    assert "No paid avatar provider" in data["rule"]


def test_post_contract_returns_avatar_contract(client):
    set_llm_provider(
        ScriptedProvider(
            [
                decision(
                    {
                        "intent": "VIEW_CHILD_ATTENDANCE",
                        "entities": {"student_name": "Rahul"},
                        "tool_calls": [
                            {
                                "name": "get_child_attendance",
                                "arguments": {"student_id": "s1"},
                            }
                        ],
                    }
                ),
                LLMResponse(text="Rahul was present on 10 Aug.", finish_reason="STOP"),
            ]
        )
    )

    response = client.post(
        "/api/v1/avatar/contract",
        json={"message": "How much attendance does my child have?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    data = body["data"]
    # Exact Section 15 field set (audio included, null in V1).
    assert set(data) == {
        "conversation_id",
        "message_id",
        "text",
        "language",
        "persona",
        "avatar",
        "audio",
    }
    assert data["text"] == "Rahul was present on 10 Aug."
    assert data["language"] == "en-IN"
    assert data["persona"] == "parent"
    assert data["avatar"] == {"state": "speaking", "emotion": "friendly"}
    assert data["audio"] == {"url": None, "duration": None}


def test_post_contract_requires_authentication():
    with TestClient(create_app()) as unauth:
        response = unauth.post(
            "/api/v1/avatar/contract", json={"message": "Hi"}
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
