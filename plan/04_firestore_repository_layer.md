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

# SECTION 04 — FIRESTORE REPOSITORY LAYER

## Assigned coder

Database Coder

## Goal

Create the generic Firestore access layer.

## In Scope

- Firebase Admin Firestore initialization
- repositories
- typed conversion helpers
- timestamps
- pagination helpers where needed
- error mapping

## Out of Scope

Business rules.

The repository must not decide:

```text
Is this parent allowed to see this child?
```

That belongs to authorization/services.

## Repositories

```text
UserRepository
StudentRepository
ClassRepository
AttendanceRepository
ConversationRepository
SupportRequestRepository
AuditLogRepository
```

## Required Generic Behavior

Each repository should support relevant:

```text
get
create
update
list/query
delete
```

Do not blindly implement every CRUD method if a collection does not need it.

## Firestore Initialization

Provide:

```python
get_firestore_client()
```

or an equivalent dependency/provider.

## Acceptance Tests

Use a testable approach:

- mocks/fakes for unit tests
- integration tests where practical
- correct document mapping
- error handling

## Important

No API route should contain raw Firestore code.

No AI tool should contain raw Firestore code.

---
