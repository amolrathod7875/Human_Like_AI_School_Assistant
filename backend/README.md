# XYZ AI — Backend (Section 01: Python / FastAPI Foundation)

Base FastAPI application that all other modules plug into. This module owns only
the shared infrastructure: app factory, configuration, error handling, request
IDs, structured logging, response envelopes, CORS, lifecycle, and a health
endpoint.

## Stack

Python 3.11, FastAPI, Pydantic v2, pydantic-settings, Uvicorn.

## Project layout

```text
backend/
├── app/
│   ├── main.py              # app factory, middleware, exception handlers, lifespan
│   ├── core/
│   │   ├── config.py        # Settings / get_settings / settings singleton
│   │   ├── errors.py        # AppError, RequestContext (contextvar-backed)
│   │   ├── logging.py       # structured, request-aware logging
│   │   └── responses.py     # ApiResponse envelope + helpers
│   ├── api/v1/              # versioned routers (health lives here)
│   ├── services/            # (reserved for other modules)
│   ├── repositories/        # (reserved)
│   ├── providers/           # (reserved, adapters for external services)
│   ├── ai/                  # persona/language, tool registry, orchestrator
│   ├── auth/                # (reserved)
│   └── schemas/             # (reserved)
├── tests/                   # pytest suite + conftest
├── scripts/                 # (reserved)
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## Modules

- **auth** (`app/auth`): Firebase ID-token verification, `AuthenticatedUser`, and the
  reusable `get_authenticated_user` dependency. See [`app/auth/README.md`](app/auth/README.md).
- **user service** (`app/services`): profiles, roles, and relationships backed by the
  Firestore `users` collection, behind a `UserRepository` adapter. See
  [`app/services/README.md`](app/services/README.md).
- **firestore repository layer** (`app/repositories`): generic typed
  `FirestoreRepository[T]` base (CRUD, mapping, timestamps, pagination, error
  mapping) plus the 7 concrete repositories and `get_firestore_client()`. See
  [`app/repositories/README.md`](app/repositories/README.md).
- **authorization engine** (`app/auth/authorization`): `AuthorizationContext`,
  context builder (authoritative stored identity), and the 6 explicit policy
  functions + `enforce()`. See
  [`app/auth/authorization/README.md`](app/auth/authorization/README.md).
- **conversation & memory engine** (`app/services/conversation_service`):
  `create_conversation`, `get_conversation`, `append_message`,
  `get_recent_messages`, `build_context`, and `ConversationContext`. Ownership
  enforced via the authorization context; messages stored in the
  `conversations/{id}/messages` subcollection. See
  [`app/services/README.md`](app/services/README.md).
- **Cohere LLM provider** (`app/providers/cohere`): `LLMProvider` interface,
  `LLMRequest`/`LLMResponse`, `CohereProvider` (SDK wrapper, timeouts, retries,
  error/response mapping), and `MockLLMProvider`. See
  [`app/providers/cohere/README.md`](app/providers/cohere/README.md).
- **persona + language manager** (`app/ai/persona`): `get_persona`,
  `normalize_language`, `get_language_instruction`. Role-based tone/phrasing
  only; safe English fallback for unsupported languages. See
  [`app/ai/persona/README.md`](app/ai/persona/README.md).
- **AI tool registry** (`app/ai/tools`): `AITool`/`BaseTool`, `register_tool`,
  `get_tool`, `list_tools`, `list_tool_definitions`, `execute_tool`, and a typed
  execution pipeline (exists → validate args → authorize → execute → validate
  result). Provider-independent (no Cohere import). See
  [`app/ai/tools/README.md`](app/ai/tools/README.md).
- **attendance domain** (`app/services/attendance_service`): `get_student_attendance`,
  `get_child_attendance`, `mark_attendance`, `get_overall_attendance`, and
  `resolve_student_reference` (handles duplicate-name ambiguity). Enforces the
  Section 05 policies; `teacher_id` is taken from the stored identity, not the
  request body. Four AI tool adapters (`get_own_attendance`, `get_child_attendance`,
  `get_overall_attendance`, `mark_attendance`) and REST routes under
  `/api/v1/attendance`. See [`app/services/README.md`](app/services/README.md).
- **AI orchestrator** (`app/ai/orchestrator`): `handle_message` — the central
  natural-language turn (conversation → persona/language → Cohere intent decision
  → validated registry tool call with authorization → natural response →
  persisted messages → structured response with avatar hint), exposed as
  `POST /api/v1/ai/chat`. Never the authorization authority. See
  [`app/ai/orchestrator/README.md`](app/ai/orchestrator/README.md).
- **AI security / prompt-injection** (`app/security`): explicit defenses for the
  whole pipeline — `log_security_event` (markers `SECURITY_EVENT`,
  `AUTHORIZATION_DENIED`, `TOOL_REJECTED`, `SUSPICIOUS_INPUT`), suspicious-input
  detection, and secret redaction of model output and tool arguments. See
  [`app/security/README.md`](app/security/README.md).
- **Escalation / human support** (`app.services.escalation_service`): teacher/
  management support-request workflow. Persists to `support_requests` and dispatches
  via a `HumanSupportAdapter` (mock by default — no paid provider). Exposed as
  `POST /api/v1/escalation/request` and `GET /api/v1/escalation/{request_id}`, and
  as the `create_teacher_contact_request` / `create_management_contact_request`
  orchestrator tools. See [`app/services/README.md`](app/services/README.md).

## Running locally

```powershell
conda activate vidhoor            # or your env
pip install -r requirements.txt
cp .env.example .env              # adjust as needed
uvicorn app.main:app --reload --port 8000
```

Health check:

```http
GET /api/v1/health
```

```json
{
  "success": true,
  "data": { "service": "xyz-ai-backend", "status": "healthy" }
}
```

## How other modules import the foundation

```python
from app.core.config import settings          # typed app settings (singleton)
from app.core.errors import AppError, RequestContext
from app.core.responses import ApiResponse, success_response, error_response
```

To register a new v1 router, add it in `app/api/v1/__init__.py`:

```python
from app.api.v1 import health, my_module
api_router.include_router(my_module.router, tags=["my_module"])
```

## Shared contracts

### `Settings` (`app.core.config`)
Pydantic settings loaded from environment / `.env`. See `.env.example`.

### `AppError` (`app.core.errors`)
Raise for domain errors; the global handler serializes it to the standard error
envelope with the active request id.

```python
raise AppError("NOT_FOUND", "Thing not found", status_code=404)
```

### `RequestContext` (`app.core.errors`)
Per-request context (request id) backed by a `contextvars.ContextVar`, so it is
isolated across concurrent requests. Set automatically by the request-id
middleware; read in logs and errors.

### `ApiResponse[T]` (`app.core.responses`)
Generic envelope: `{ success, data?, error? }`. Build with
`success_response(data)` and `error_response(code, message, status_code=...)`.

## Error envelope

```json
{
  "success": false,
  "error": { "code": "SOME_ERROR", "message": "Human-readable", "request_id": "req_123" }
}
```

## Request IDs

Each request gets (or reuses) an `X-Request-ID` header value (`req_<uuid>` when
absent). The value is echoed in the response header, injected into every log
record (`[req_id=...]`), and returned in error payloads.

## CORS

Configurable via `BACKEND_CORS_ORIGINS` (comma-separated or JSON array). Defaults
to `["*"]` for local development.

## Environment variables

See `.env.example`. Required by this module:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PROJECT_NAME` | `xyz-ai-backend` | App/OpenAPI title |
| `SERVICE_NAME` | `xyz-ai-backend` | Reported by health endpoint |
| `ENVIRONMENT` | `development` | Runtime environment label |
| `DEBUG` | `false` | Enables docs/openapi when true |
| `API_V1_PREFIX` | `/api/v1` | API version prefix |
| `BACKEND_CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Root log level |
| `REQUEST_ID_HEADER` | `X-Request-ID` | Header used for request id |

## Tests

```powershell
pytest                          # uses pytest.ini (pythonpath = .)
```

Covers: server start, health endpoint, request-id presence, client-supplied
request id, standardized 404 error, standardized 422 validation error, and CORS
header emission.

## Out of scope (owned by other modules)

Firebase auth, Firestore, Cohere, Vapi, AI orchestration, frontend.
