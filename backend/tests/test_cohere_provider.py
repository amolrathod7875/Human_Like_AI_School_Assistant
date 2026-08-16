import asyncio
import types

import pytest

from app.providers.cohere.errors import LLMProviderError
from app.providers.cohere.models import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolDefinition,
)
from app.providers.cohere.mock import MockLLMProvider
from app.providers.cohere.provider import CohereProvider, get_llm_provider, set_llm_provider


def _request():
    return LLMRequest(
        messages=[LLMMessage(role="user", content="How much attendance does Rahul have?")],
        system_instructions="You are a helpful school assistant.",
        language_instruction="Respond in English.",
    )


def _fake_raw(text="Rahul has 91.2% attendance.", finish="COMPLETE", tool_calls=None):
    return types.SimpleNamespace(
        finish_reason=finish,
        message=types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text=text)],
            tool_calls=tool_calls or [],
        ),
    )


class FakeClient:
    def __init__(self, raw, fail_with=None, calls=None):
        self.raw = raw
        self.fail_with = fail_with
        self.calls = calls if calls is not None else []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail_with is not None:
            raise self.fail_with
        return self.raw


def test_provider_initializes_without_sdk_call():
    provider = CohereProvider(api_key="test-key", model="command-r", timeout=10, max_retries=2)
    assert provider.api_key == "test-key"
    assert provider.model == "command-r"
    assert provider.timeout == 10
    assert provider.max_retries == 2


def test_successful_generation_maps_response():
    client = FakeClient(raw=_fake_raw())
    provider = CohereProvider(api_key="k", client=client)

    resp = asyncio.run(provider.generate(_request()))

    assert isinstance(resp, LLMResponse)
    assert resp.text == "Rahul has 91.2% attendance."
    assert resp.finish_reason == "STOP"
    assert resp.tool_calls == []
    # The SDK was actually invoked once.
    assert len(client.calls) == 1
    # System prompt composed from instructions/context.
    assert "system" in client.calls[0]
    assert "helpful school assistant" in client.calls[0]["system"]


def test_tool_calls_mapped():
    raw = _fake_raw(
        text=None,
        finish="TOOL_CALL",
        tool_calls=[
            types.SimpleNamespace(
                id="call_1",
                function=types.SimpleNamespace(
                    name="view_attendance", arguments={"student": "Rahul"}
                ),
            )
        ],
    )
    client = FakeClient(raw=raw)
    provider = CohereProvider(api_key="k", client=client)

    resp = asyncio.run(provider.generate(_request()))

    assert resp.finish_reason == "TOOL_CALL"
    assert resp.tool_calls == [
        LLMToolCall(id="call_1", name="view_attendance", arguments={"student": "Rahul"})
    ]


def test_api_failure_raises_provider_error():
    client = FakeClient(raw=None, fail_with=RuntimeError("boom"))
    provider = CohereProvider(api_key="k", client=client, max_retries=0)

    with pytest.raises(LLMProviderError) as exc:
        asyncio.run(provider.generate(_request()))
    assert exc.value.retryable is False


def test_timeout_is_retryable_and_retries():
    client = FakeClient(raw=None, fail_with=TimeoutError("timed out"), calls=[])
    provider = CohereProvider(api_key="k", client=client, max_retries=2)

    with pytest.raises(LLMProviderError) as exc:
        asyncio.run(provider.generate(_request()))
    assert exc.value.retryable is True
    # max_retries=2 -> 3 attempts total.
    assert len(client.calls) == 3


def test_malformed_response_raises():
    client = FakeClient(raw=types.SimpleNamespace())  # no .message
    provider = CohereProvider(api_key="k", client=client, max_retries=0)

    with pytest.raises(LLMProviderError):
        asyncio.run(provider.generate(_request()))


def test_mock_provider_returns_scripted_response():
    mock = MockLLMProvider(
        response=LLMResponse(text="mocked", finish_reason="STOP")
    )
    resp = asyncio.run(mock.generate(_request()))
    assert resp.text == "mocked"
    assert resp.finish_reason == "STOP"


def test_get_set_llm_provider_injection():
    original = get_llm_provider()
    mock = MockLLMProvider()
    set_llm_provider(mock)
    try:
        assert get_llm_provider() is mock
        resp = asyncio.run(get_llm_provider().generate(_request()))
        assert resp.text == "mock response"
    finally:
        set_llm_provider(original)
