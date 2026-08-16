import pytest

from app.providers.vapi.errors import VapiError
from app.providers.vapi.models import NormalizedVoiceEvent
from app.providers.vapi.normalizer import (
    normalize_event,
    normalize_response,
    resolve_conversation_id,
    safe_message,
)
from app.ai.orchestrator.schemas import ChatResponse


def test_tool_calls_event_with_voice_tool_is_reply():
    raw = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "call_1", "metadata": {"user_id": "fb_42",
                                                  "language": "hi-IN"}},
            "toolCallList": [
                {"id": "tc1", "name": "process_voice",
                 "parameters": {"transcript": "मेरे बच्चे की उपस्थिति?"}},
                {"id": "tc2", "name": "other_tool", "parameters": {}},
            ],
        }
    }
    event = normalize_event(raw)
    assert event.requires_reply is True
    assert event.transcript == "मेरे बच्चे की उपस्थिति?"
    assert event.tool_call_id == "tc1"
    assert event.tool_name == "process_voice"
    assert event.firebase_uid == "fb_42"
    assert event.language == "hi-IN"
    assert event.call_id == "call_1"


def test_tool_calls_without_voice_tool_is_not_reply():
    raw = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "call_2"},
            "toolCallList": [{"id": "x", "name": "send_email",
                              "parameters": {"to": "a@b.c"}}],
        }
    }
    event = normalize_event(raw)
    assert event.requires_reply is False
    assert event.transcript is None


def test_transcript_event_is_informational_only():
    raw = {
        "message": {
            "type": "transcript",
            "role": "user",
            "transcriptType": "final",
            "transcript": "hello there",
            "call": {"id": "call_3", "metadata": {"user_id": "fb_9"}},
        }
    }
    event = normalize_event(raw)
    assert event.requires_reply is False
    assert event.transcript is None


def test_transcript_combined_type_is_informational():
    raw = {"message": {"type": "transcript[transcriptType=\"final\"]",
                       "call": {"id": "call_4"}}}
    event = normalize_event(raw)
    assert event.requires_reply is False
    assert event.event_type.startswith("transcript")


def test_unwrapped_payload_is_supported():
    raw = {"type": "tool-calls", "call": {"id": "c5"},
           "toolCallList": [{"id": "t", "name": "process_voice",
                             "parameters": {"transcript": "hi"}}]}
    event = normalize_event(raw)
    assert event.requires_reply is True
    assert event.transcript == "hi"


def test_malformed_payload_raises():
    with pytest.raises(VapiError):
        normalize_event("not a dict")
    with pytest.raises(VapiError):
        normalize_event({"message": [1, 2, 3]})


def test_resolve_conversation_id_prefers_metadata_then_call():
    explicit = NormalizedVoiceEvent(event_type="tool-calls",
                                    call_id="c", metadata={},
                                    conversation_id="conv_x",
                                    requires_reply=True)
    assert resolve_conversation_id(explicit) == "conv_x"

    by_call = NormalizedVoiceEvent(event_type="tool-calls", call_id="c123",
                                   metadata={}, requires_reply=True)
    assert resolve_conversation_id(by_call) == "vapi:c123"

    anon = NormalizedVoiceEvent(event_type="tool-calls", metadata={},
                                requires_reply=True)
    assert resolve_conversation_id(anon) == "vapi:anonymous"


def test_normalize_response_shape():
    event = NormalizedVoiceEvent(event_type="tool-calls", call_id="c",
                                 tool_call_id="tc1", tool_name="process_voice",
                                 requires_reply=True)
    chat = ChatResponse(conversation_id="conv1", message_id="m1",
                        text="Rahul was present.", language="hi-IN",
                        persona="parent")
    out = normalize_response(event, chat)
    assert out == {
        "results": [
            {"name": "process_voice", "toolCallId": "tc1",
             "result": "Rahul was present."}
        ]
    }


def test_normalize_response_falls_back_to_safe_message():
    event = NormalizedVoiceEvent(event_type="tool-calls", call_id="c",
                                 tool_call_id="tc1", tool_name="process_voice",
                                 requires_reply=True)
    chat = ChatResponse(conversation_id="conv1", message_id="m1", text="",
                        language="en-IN", persona="parent")
    out = normalize_response(event, chat)
    assert out["results"][0]["result"] == safe_message("unavailable")


def test_safe_message_keys():
    assert safe_message("unavailable")
    assert safe_message("account_unidentified")
    assert safe_message("account_error")
