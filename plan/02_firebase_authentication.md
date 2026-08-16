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

# SECTION 02 — FIREBASE AUTHENTICATION

## Assigned coder

Authentication Coder

## Goal

Verify Firebase Authentication tokens in Python.

## In Scope

- Firebase Admin SDK
- token verification
- auth dependency
- user identity extraction
- protected route helper
- `/auth/me`

## Out of Scope

- role authorization policies
- attendance authorization
- frontend Firebase login UI

## Required Environment Variables

Document the secure method for:

```text
FIREBASE_PROJECT_ID
FIREBASE_CLIENT_EMAIL
FIREBASE_PRIVATE_KEY
```

Use the actual method required by the final deployment.

## Auth Context

Define:

```python
AuthenticatedUser:
    firebase_uid: str
    email: str | None
    name: str | None
```

Do not put the application role here yet unless Section 03 explicitly extends the context.

## Endpoint

```http
GET /api/v1/auth/me
Authorization: Bearer <firebase_id_token>
```

## Failure Cases

- no token
- malformed token
- expired token
- invalid token
- revoked token if supported

Use appropriate HTTP status codes.

## Security Requirements

Never log raw bearer tokens.

Never accept a client-supplied Firebase UID as authoritative identity.

## Acceptance Tests

- valid Firebase token
- invalid token
- expired token
- missing token
- protected endpoint without token

## Handoff Contract

Provide a reusable dependency:

```python
get_authenticated_user()
```

---
