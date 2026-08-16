# XYZ AI — Kilo Code Task

## Global Rules

This file is one independent backend work package for XYZ AI.

You are one coder in a multi-coder development workflow. Implement ONLY the scope defined in this file.

### Mandatory rules

1. Do not rewrite unrelated modules.
2. Do not silently change shared contracts.
3. Never hardcode secrets.
4. Never log API keys, tokens, passwords, or private keys.
5. Use the existing Python/FastAPI architecture.
6. Use typed Pydantic schemas where applicable.
7. Keep external providers behind adapters/interfaces.
8. The LLM must never directly access Firestore.
9. The LLM must never be the final authorization authority.
10. Never trust a client-supplied role.
11. Do not add RAG or a vector database.
12. Do not build frontend code.
13. Write tests for the module you implement.
14. Update module documentation/README where appropriate.
15. Do not introduce paid services.
16. At completion, provide a handoff report:
    - files created
    - files modified
    - APIs added
    - interfaces added
    - Firestore collections touched
    - environment variables required
    - dependencies added
    - tests added
    - integration dependencies
    - known limitations
    - contract changes, if any

## Locked Stack

```text
Coding              Kilo Code
Backend             Python + FastAPI
LLM                 Cohere API
STT / TTS           Vapi
Authentication      Firebase Authentication
Database            Firebase Firestore
Backend Hosting     Hugging Face Spaces
Frontend            Lovable AI
Frontend Hosting    Vercel
RAG                 Not required for V1
Vector Database     Not required for V1
AI Avatar           Frontend-based interactive avatar
Architecture        Modular monolith
```

# SECTION 01 — PYTHON / FASTAPI FOUNDATION

## Assigned coder

Backend Infrastructure Coder

## Goal

Create the base FastAPI application that all other modules can plug into.

## In Scope

- FastAPI application
- application startup/shutdown
- API versioning
- configuration
- CORS
- exception handling
- request IDs
- structured logging
- base response utilities
- health endpoint
- base test setup

## Out of Scope

- Firebase authentication
- Firestore business logic
- Cohere
- Vapi
- attendance
- AI orchestration
- frontend

## Required Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── errors.py
│   │   ├── logging.py
│   │   └── responses.py
│   ├── api/
│   │   └── v1/
│   ├── services/
│   ├── repositories/
│   ├── providers/
│   ├── ai/
│   ├── auth/
│   └── schemas/
├── tests/
├── scripts/
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## Endpoints

```http
GET /api/v1/health
```

Expected:

```json
{
  "success": true,
  "data": {
    "service": "xyz-ai-backend",
    "status": "healthy"
  }
}
```

## Shared Infrastructure Requirements

Create:

```python
Settings
AppError
RequestContext
ApiResponse
```

## Request ID

Each request should receive or generate a request ID.

Use it in logs and errors.

## Error Format

Use a consistent structure:

```json
{
  "success": false,
  "error": {
    "code": "SOME_ERROR",
    "message": "Human-readable message",
    "request_id": "req_123"
  }
}
```

## Acceptance Tests

- server starts
- health endpoint works
- invalid endpoint returns standardized error
- validation error is standardized
- request ID is present
- CORS is configurable

## Handoff

Other agents must be able to import:

```python
from app.core.config import settings
from app.core.errors import AppError
```

---
