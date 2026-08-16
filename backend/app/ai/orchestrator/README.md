# Section 11 — AI Orchestrator

The central natural-language workflow. It turns one authenticated user message
into a validated intent, an authorized tool call, a persisted conversation turn,
and a structured response the frontend/avatar can render.

**The orchestrator is not the authorization engine.** Every action goes through
the Section 09 tool registry, which validates arguments and applies the
Section 05 policies. A refusal there is a refusal here.

## Entry point

```python
from app.ai.orchestrator import ChatRequest, handle_message

response = await handle_message(context, ChatRequest(message="..."))
```

`context` is the caller's `AuthorizationContext`, built from the **stored**
Firestore profile (never from the client, the token claims, or the model).
`provider=` may be passed to inject an `LLMProvider` (tests); otherwise
`get_llm_provider()` is used.

## API

```http
POST /api/v1/ai/chat
```

Request:

```json
{ "conversation_id": "conv_001", "message": "How much attendance does my child have?" }
```

`conversation_id` is optional — a new conversation is created when it is absent.
`language` is an optional hint applied only when creating a new conversation.
Any other field (including `role` or `user_id`) is ignored.

Response (inside the standard `ApiResponse` envelope):

```json
{
  "conversation_id": "conv_001",
  "message_id": "msg_003",
  "text": "Rahul currently has 91.2% attendance.",
  "language": "en-IN",
  "persona": "parent",
  "tool_calls": [{ "name": "get_child_attendance", "status": "OK", "message": null }],
  "avatar": { "state": "speaking", "emotion": "friendly" }
}
```

## Processing flow

```text
authenticated context (role from stored profile)
  → load / create conversation      (ownership enforced by Section 06)
  → load conversation context       (recent turns, known entities, prior results)
  → load language + persona         (Section 08)
  → LLM pass 1: intent / entities / requested tools   (Section 07 adapter)
  → validate model output           (intent allowlist, entity allowlist, shape)
  → tool registry: exists → validate args → AUTHORIZE → execute → validate result
  → LLM pass 2: natural response from sanitized tool results
  → persist user / tool / assistant messages
  → structured response (+ avatar hint)
```

Turns without a tool call (greetings, general questions, clarifications) use a
single LLM pass; only tool turns need the second pass.

## Intents

`VIEW_OWN_ATTENDANCE`, `VIEW_CHILD_ATTENDANCE`, `MARK_ATTENDANCE`,
`VIEW_SCHOOL_ATTENDANCE`, `REQUEST_TEACHER_CONTACT`,
`REQUEST_MANAGEMENT_CONTACT`, `GENERAL_QUERY`.

Anything else the model returns is normalized to `GENERAL_QUERY`
(`normalize_intent`). The escalation intents map to the Section 13 tools; while
those are unregistered the call is reported as `UNAVAILABLE` and the reply says
the capability is not available yet — it never claims a human was contacted.

## Entity extraction

Accepted keys only: `student_name`, `student_id`, `date`, `date_range`,
`class_id`, `reason`. Extracted entities are stored on the user message, so
follow-up turns (`build_context`) can reuse them.

## Missing / ambiguous information

Never guessed. Two paths produce a clarifying question:

- the model reports `missing_information` / `clarification_question` and requests
  no tool;
- a tool rejects the arguments (e.g. `resolve_student_reference` found several
  students named "Rahul") → status `NEEDS_CLARIFICATION`.

```text
"Mark Rahul absent."  →  "Please clarify which Rahul you mean."
```

Nothing is written in that case.

## Tool call statuses

| Status | Meaning | Reply guarantee |
| --- | --- | --- |
| `OK` | executed, result validated | may state the result |
| `DENIED` | authorization refused it | states no data, no success |
| `NEEDS_CLARIFICATION` | missing/ambiguous arguments | asks one question |
| `UNAVAILABLE` | tool not registered | says not available yet |
| `ERROR` | execution/validation failure | says it could not be completed |

Only `name`, `status`, and a generic `message` are returned to the client. The
model-proposed arguments and raw results are persisted server-side for audit.

## Security properties

- Authorization is authoritative: `execute_tool` runs the registry hook and the
  tool's `authorize()` (Section 05 policies) on every call.
- Only registered tools run; an unknown name is never executed.
- Tool arguments are schema-validated by the tool's `input_schema`; results are
  validated by `output_schema` before they enter the generation context.
- Model output can never change identity: role/permission-like keys are dropped
  from entities and logged as `SECURITY_EVENT`. The response persona and the
  conversation role always come from the stored profile.
- Prompts carry no secrets — only role, persona, language, the caller's own
  scope (their child ids, class ids, ...), conversation history, and validated
  tool results.
- The model is offered only the tools relevant to the caller's role
  (`tools_for_role`), as defense in depth on top of authorization.
- Failures are sanitized: users and the model see generic messages, never raw
  exceptions, other users' data, or internal rules.
- Logs use `SECURITY_EVENT`, `AUTHORIZATION_DENIED`, and `TOOL_REJECTED` markers
  and never include tokens, keys, or credentials.
- Per-turn limits: message length (4000 chars → 422), tool calls
  (`AI_MAX_TOOL_CALLS`), history (`AI_CONTEXT_MESSAGE_LIMIT`), and tool result
  size (50 items, then truncated with a marker).
- If the LLM provider is unavailable the turn degrades to a fixed safe message
  and, after a tool call, to a deterministic status-based reply — never a guess
  and never a false success claim.

## Persistence (Section 06 collections)

Per turn, in `conversations/{id}/messages`:

1. `user` — the raw message, `intent`, extracted `entities`;
2. `tool` — proposed `tool_calls` and sanitized `tool_results` (only when a tool ran);
3. `assistant` — the final text; its id is the returned `message_id`.

## Avatar hint

`state` is `speaking`; `emotion` is `concerned` for denials/errors/unavailable or
a provider failure, `neutral` when clarifying, `friendly` for student/parent, and
`professional` for teacher/principal. It is presentation metadata only (see
Section 15).

## Modules

```text
app/ai/orchestrator/
├── orchestrator.py   # handle_message: the full turn
├── intents.py        # Intent enum, entity allowlist, intent/role tool maps
├── prompt.py         # guardrailed system instructions + non-secret context
├── validation.py     # parse/sanitize model output (JSON or native tool calls)
└── schemas.py        # ChatRequest/ChatResponse, tool records, avatar hint
```

## Settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `AI_CONTEXT_MESSAGE_LIMIT` | `10` | conversation turns given to the model |
| `AI_MAX_TOOL_CALLS` | `3` | tool calls allowed in one turn |

No new secrets: the Cohere key stays in `COHERE_API_KEY` (Section 07).

## Tests

- `tests/test_ai_orchestrator.py` — happy-path parent flow, native tool calls,
  single-pass general query, denial paths (student marking, parent analytics,
  another person's child), role-claim injection, inactive user, other users'
  conversations, ambiguity/missing information, successful teacher marking,
  unregistered tool, provider failure (both passes), raw-JSON leak protection,
  history reuse, role-scoped tool definitions, tool-call cap, unknown intent,
  language hint, secret-free prompts, plus unit tests for entity sanitizing,
  JSON extraction, and role tool scoping.
- `tests/test_ai_chat_api.py` — response contract/shape, conversation
  continuation, empty and oversized message rejection, inactive user, missing
  authentication, and client-supplied role being ignored.
