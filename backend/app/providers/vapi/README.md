# Section 14 — Vapi Voice Integration

Voice adapter + webhook layer that converges spoken input into the **same AI
orchestrator** used by chat. Voice is not a separate authorization path: the
orchestrator, its tool registry, the authorization engine, and persona pipeline
are shared. Vapi performs STT/TTS only; this backend stays the brain.

## Architecture

```text
User voice
   ↓ (STT)
Vapi
   ↓ POST /api/v1/voice/webhook   (HMAC-signed)
Vapi adapter  → verify → normalize
   ↓
AI Orchestrator   ← same path as POST /api/v1/ai/chat
   ↓
ChatResponse → adapter normalizes → Vapi "results"  (TTS)
```

```text
CHAT ──────┐
            ▼
       AI ORCHESTRATOR
            ▲
VOICE ─────┘
```

## Components

- `providers/vapi/errors.py` — `VapiError` / `VapiWebhookError` (provider-local;
  translated to `AppError` at the API boundary).
- `providers/vapi/models.py` — `NormalizedVoiceEvent` (provider-neutral event).
- `providers/vapi/verifier.py` — `VapiWebhookVerifier` (Protocol),
  `VapiSignatureVerifier` (HMAC-SHA256 over the raw body using
  `VAPI_WEBHOOK_SECRET`, constant-time compare), `NoopVerifier` (dev/tests).
- `providers/vapi/normalizer.py` — `normalize_event` (raw Vapi payload →
  `NormalizedVoiceEvent`), `normalize_response` (`ChatResponse` → Vapi `results`),
  `resolve_conversation_id`, `safe_message`.
- `providers/vapi/provider.py` — `VapiAdapter` (verify + normalize boundary).
- `services/voice_service.py` — `handle_voice_turn` (calls the orchestrator).
- `api/v1/voice.py` — `POST /voice/webhook` and `POST /voice/respond`.

## Webhook contract

Vapi sends `POST` with body `{"message": {"type": ..., "call": {...}, ...}}`.

- **`tool-calls`** (the brain path): the assistant is configured with one tool
  (`VAPI_VOICE_TOOL_NAME`, default `process_voice`) whose parameter is the user's
  transcript. The adapter extracts the transcript and runs the orchestrator, then
  returns:
  ```json
  { "results": [ { "name": "process_voice", "toolCallId": "<id>",
                   "result": "<spoken reply>" } ] }
  ```
  Vapi speaks `result`.
- **`transcript`** (and all other events) are **informational** and acknowledged
  with `{"received": true}` — they never trigger a reply, so the orchestrator
  remains the single brain.

## Authentication strategy

- **Provider authenticity:** every inbound webhook is verified against the
  `X-Vapi-Signature` HMAC (Vapi signs the raw body with `VAPI_WEBHOOK_SECRET`).
  Missing/invalid signature → `401`. With no configured secret and
  `VAPI_WEBHOOK_VERIFY=true` the verifier fails closed. Tests inject
  `NoopVerifier` via `set_vapi_webhook_verifier(...)`.
- **Caller identity:** taken ONLY from the call's **server-side metadata**
  (`call.metadata.user_id` / `user_id` set by us when the call is created), never
  from the transcript. It is resolved through the exact same
  `get_authorization_context` used by chat, so role/active/relationship come from
  the stored Firestore profile — never trusted from the request. A webhook
  without a resolvable identity gets a safe spoken message; no privileged action
  is permitted.
- `POST /voice/respond` is a normal bearer-authenticated endpoint (mirrors chat)
  for clients that already have a token and want the TTS-ready reply.

## Conversation & language propagation

- `conversation_id` comes from `call.metadata.conversation_id` when present;
  otherwise it is derived as `vapi:<call.id>` so every turn of one phone call
  shares a conversation (ownership enforced by the conversation engine).
- `language` comes from `call.metadata.language` (e.g. `"hi-IN"`) and is applied
  only when a new conversation is created — phrasing only, never authorization.

## Configuration (env vars)

| Variable | Default | Purpose |
| --- | --- | --- |
| `VAPI_WEBHOOK_SECRET` | – | HMAC secret for inbound webhook verification (secret) |
| `VAPI_API_KEY` | – | Optional REST API key for outbound Vapi calls (secret) |
| `VAPI_VOICE_TOOL_NAME` | `process_voice` | Assistant tool that forwards the transcript |
| `VAPI_WEBHOOK_VERIFY` | `true` | Require a valid `X-Vapi-Signature` |

## Tests

`tests/test_vapi_webhook.py` (valid tool-call event, invalid signature, malformed
transcript, language propagation, conversation propagation, authorization still
enforced) and `tests/test_vapi_normalizer.py` (payload normalization).
