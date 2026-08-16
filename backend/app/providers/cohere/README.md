# Section 07 — Cohere LLM Provider

Clean, provider-independent LLM layer. **Only this module imports the Cohere
SDK**; the rest of the project depends on the `LLMProvider` interface and the
normalized `LLMRequest` / `LLMResponse` models.

## Models (`app.providers.cohere.models`)

- `LLMRequest` — `messages`, `system_instructions`, `user_context`,
  `tool_definitions`, `language_instruction`, `persona_instruction`,
  `temperature`, `max_tokens`, `model`. No secrets.
- `LLMResponse` — `text`, `tool_calls` (`LLMToolCall`), `finish_reason`.
- `LLMMessage`, `LLMToolDefinition`, `LLMToolCall`.

## Interface

```python
class LLMProvider(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
```

## `CohereProvider`

- Wraps `cohere.ClientV2` (imported lazily; SDK never imported elsewhere).
- The blocking SDK call runs in a thread (`asyncio.to_thread`) so `generate` is
  `async`.
- Honors `COHERE_API_KEY` / `COHERE_MODEL` / `COHERE_TIMEOUT` / `COHERE_MAX_RETRIES`
  (overridable per instance).
- **Retries only safe failures**: timeouts, connection errors, and HTTP
  `429/500/502/503`. Auth/validation errors are not retried.
- Normalizes provider output: text blocks → `text`, `tool_calls` →
  `LLMToolCall`, Cohere finish reasons → `STOP` / `TOOL_CALL` / `MAX_TOKENS` /
  `ERROR`.
- Maps all SDK/transport errors to `LLMProviderError(retryable, status_code)`.
- **Never logs the API key.**

## `MockLLMProvider`

Implements `LLMProvider` for unit tests; returns scripted or fixed
`LLMResponse`s and records calls.

## Injection

`get_llm_provider()` / `set_llm_provider(provider)` allow swapping the default
`CohereProvider` for a `MockLLMProvider` in tests or alternative providers later.

## Tests

`tests/test_cohere_provider.py` covers: provider initialization (no SDK call),
successful generation with a fake client (text/tool_calls/finish_reason
mapping), API failure → `LLMProviderError`, timeout → retryable error with
retries attempted, malformed response → `LLMProviderError`, and mocked
generation via `MockLLMProvider`.
