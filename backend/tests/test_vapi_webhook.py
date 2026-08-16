import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.cohere.models import LLMResponse
from app.providers.cohere.provider import set_llm_provider
from app.providers.vapi import (
    VapiAdapter,
    NoopVerifier,
    VapiSignatureVerifier,
    set_vapi_adapter,
    set_voice_session_store,
    InMemoryVoiceSessionStore,
)
from app.providers.vapi.verifier import VAPI_SIGNATURE_HEADER
from app.schemas.collections import AttendanceRecord
from app.schemas.user import Role
from app.services import attendance_service as att_svc
from app.services import conversation_service as conv_svc
from app.ai.orchestrator.orchestrator import MSG_DENIED
from tests.test_ai_orchestrator import (
    STUDENTS,
    FakeConversationRepo,
    FakeMessageRepo,
    FakeAttendanceRepo,
    FakeStudentRepo,
    ScriptedProvider,
    ctx,
)
from app.ai.tools.attendance_tools import (
    GetChildAttendanceTool,
    GetOverallAttendanceTool,
    GetOwnAttendanceTool,
    MarkAttendanceTool,
)
from app.ai.tools.registry import register_tool, reset_registry
import app.api.v1.voice as voice_module


def decision(intent, *, tool_calls=None, response_text=None, entities=None):
    payload = {"intent": intent}
    if tool_calls is not None:
        payload["tool_calls"] = tool_calls
    if entities is not None:
        payload["entities"] = entities
    if response_text is not None:
        payload["response_text"] = response_text
    return LLMResponse(text=json.dumps(payload), finish_reason="STOP")


def reply(text):
    return LLMResponse(text=text, finish_reason="STOP")


@pytest.fixture
def voice_env():
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
    reset_registry()
    register_tool(GetOwnAttendanceTool())
    register_tool(GetChildAttendanceTool())
    register_tool(GetOverallAttendanceTool())
    register_tool(MarkAttendanceTool())
    set_vapi_adapter(VapiAdapter(verifier=NoopVerifier()))
    set_voice_session_store(InMemoryVoiceSessionStore())

    app = create_app()
    parent = ctx(Role.PARENT, "p1", child_ids=["s1"])

    # The webhook resolves identity synchronously from call metadata; the
    # /respond endpoint resolves it via a bearer dependency. Patch both to the
    # same prebuilt parent context for the test.
    original_auth = voice_module.get_authorization_context
    voice_module.get_authorization_context = lambda *a, **k: parent
    app.dependency_overrides[voice_module.get_voice_auth_context] = lambda: parent

    with TestClient(app) as client:
        yield client, parent, msg_repos

    voice_module.get_authorization_context = original_auth
    app.dependency_overrides.clear()
    conv_svc.set_conversation_repository(None)
    conv_svc.set_message_repository_factory(None)
    att_svc.set_attendance_repository(None)
    att_svc.set_student_repository(None)
    reset_registry()
    set_vapi_adapter(None)
    set_voice_session_store(None)
    set_llm_provider(None)


def _tool_call_body(call_id, transcript, *, metadata=None, tool="process_voice"):
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": call_id, "metadata": metadata or {}},
            "toolCallList": [
                {"id": "tc1", "name": tool,
                 "parameters": {"transcript": transcript}}
            ],
        }
    }


def test_valid_voice_tool_call_returns_spoken_result(voice_env):
    client, _, msg_repos = voice_env
    set_llm_provider(
        ScriptedProvider(
            [
                decision(
                    "VIEW_CHILD_ATTENDANCE",
                    tool_calls=[{"name": "get_child_attendance",
                                 "arguments": {"student_id": "s1"}}],
                    entities={"student_name": "Rahul"},
                ),
                reply("Rahul was present on 10 Aug."),
            ]
        )
    )

    body = _tool_call_body(
        "call_123",
        "How much attendance does my child have?",
        metadata={"user_id": "fb_p1", "language": "hi-IN"},
    )
    resp = client.post("/api/v1/voice/webhook", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert data["results"][0]["toolCallId"] == "tc1"
    assert data["results"][0]["name"] == "process_voice"
    assert data["results"][0]["result"] == "Rahul was present on 10 Aug."
    # A single conversation was created and the turn was persisted.
    assert len(msg_repos) == 1


def test_invalid_signature_rejected(voice_env):
    client, _, _ = voice_env
    set_vapi_adapter(VapiAdapter(verifier=VapiSignatureVerifier("secret")))

    body = _tool_call_body("call_x", "hello")
    resp = client.post(
        "/api/v1/voice/webhook",
        json=body,
        headers={VAPI_SIGNATURE_HEADER: "invalid"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_malformed_transcript_returns_safe_reply(voice_env):
    client, _, _ = voice_env
    # Provider must NOT be invoked for an empty transcript.
    provider = ScriptedProvider(
        [LLMResponse(text="should not be used", finish_reason="STOP")]
    )
    set_llm_provider(provider)

    body = _tool_call_body("call_m", "", metadata={"user_id": "fb_p1"})
    resp = client.post("/api/v1/voice/webhook", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["result"]  # safe, non-empty message
    assert provider.calls == []


def test_language_propagation(voice_env):
    client, _, _ = voice_env
    provider = ScriptedProvider(
        [
            decision("GENERAL_QUERY", response_text="नमस्ते"),
            reply("नमस्ते"),
        ]
    )
    set_llm_provider(provider)

    body = _tool_call_body("call_lang", "नमस्ते",
                           metadata={"user_id": "fb_p1", "language": "hi-IN"})
    resp = client.post("/api/v1/voice/webhook", json=body)
    assert resp.status_code == 200
    # The decision call received the propagated language instruction.
    assert provider.calls[0].language_instruction == "Respond in Hindi."


def test_conversation_propagation_across_turns(voice_env):
    client, _, _ = voice_env
    provider = ScriptedProvider(
        [
            decision("GENERAL_QUERY", response_text="one"),
            decision("GENERAL_QUERY", response_text="two"),
        ]
    )
    set_llm_provider(provider)

    first = client.post(
        "/api/v1/voice/webhook",
        json=_tool_call_body("call_multi", "first",
                              metadata={"user_id": "fb_p1"}),
    )
    second = client.post(
        "/api/v1/voice/webhook",
        json=_tool_call_body("call_multi", "second",
                              metadata={"user_id": "fb_p1"}),
    )
    assert first.status_code == 200
    assert second.status_code == 200

    # Turn 2's decision saw the previous turn in its history (same conversation).
    decision_msgs = [m.content for m in provider.calls[1].messages]
    assert "first" in decision_msgs
    assert decision_msgs[-1] == "second"


def test_tool_authorization_still_enforced(voice_env):
    client, _, _ = voice_env
    provider = ScriptedProvider(
        [
            decision(
                "VIEW_SCHOOL_ATTENDANCE",
                tool_calls=[{"name": "get_overall_attendance",
                             "arguments": {}}],
            ),
            reply("You are not able to view school-wide data."),
        ]
    )
    set_llm_provider(provider)

    body = _tool_call_body("call_auth", "Show school attendance",
                           metadata={"user_id": "fb_p1"})
    resp = client.post("/api/v1/voice/webhook", json=body)

    assert resp.status_code == 200
    # The tool was refused by the same authorization engine used by chat.
    assert provider.calls[1].user_context["tool_results"][0]["status"] == "DENIED"
    # The spoken reply is non-empty and does NOT leak privileged data (no
    # attendance numbers/status leaked because the tool was denied).
    spoken = resp.json()["results"][0]["result"]
    assert spoken
    assert "PRESENT" not in spoken and "ABSENT" not in spoken
    # No attendance record was written (only the fixture seed remains).
    assert len(att_svc.get_attendance_repository().store) == 1


def test_respond_endpoint_requires_auth():
    with TestClient(create_app()) as client:
        resp = client.post(
            "/api/v1/voice/respond", json={"transcript": "hello"}
        )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_respond_endpoint_converges_into_orchestrator(voice_env):
    client, _, _ = voice_env
    set_llm_provider(
        ScriptedProvider(
            [
                decision(
                    "VIEW_CHILD_ATTENDANCE",
                    tool_calls=[{"name": "get_child_attendance",
                                 "arguments": {"student_id": "s1"}}],
                ),
                reply("Rahul was present."),
            ]
        )
    )

    resp = client.post(
        "/api/v1/voice/respond", json={"transcript": "my child attendance?"}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["say"] == "Rahul was present."
    assert data["text"] == "Rahul was present."
    assert data["conversation_id"]
    assert data["persona"] == "parent"
    assert data["tool_calls"][0]["status"] == "OK"
