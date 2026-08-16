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

# SECTION 13 — ESCALATION / HUMAN SUPPORT

## Assigned coder

Escalation Coder

## Goal

Implement the teacher/management support-request workflow.

## Firestore

Collection:

```text
support_requests
```

## Document

```json
{
  "request_id": "req_001",
  "requested_by": "parent_001",
  "requester_role": "PARENT",
  "target_type": "TEACHER",
  "target_id": "teacher_001",
  "student_id": "student_001",
  "reason": "Attendance concern",
  "status": "PENDING",
  "created_at": "...",
  "updated_at": "..."
}
```

## Status

```text
PENDING
CONFIRMED
FAILED
CANCELLED
```

## Tools

```text
create_teacher_contact_request
create_management_contact_request
```

## Flow

```text
User asks for human
      ↓
AI asks for confirmation
      ↓
User confirms
      ↓
Authorization
      ↓
Mock service
      ↓
CONFIRMED or FAILED
```

## Critical Rule

Never say:

```text
I contacted your teacher.
```

unless the mock service actually returned confirmation.

## APIs

```http
POST /api/v1/escalation/request
GET /api/v1/escalation/{request_id}
```

## Acceptance Tests

- parent teacher escalation
- parent management escalation
- unauthorized escalation
- confirmation requirement
- mock failure handling
- request status retrieval

---
