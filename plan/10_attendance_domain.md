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

# SECTION 10 — ATTENDANCE DOMAIN

## Assigned coder

School ERP / Attendance Coder

## Goal

Implement the primary school domain functionality.

## Attendance Status

```text
PRESENT
ABSENT
LATE
```

## Firestore

Collection:

```text
attendance
```

Document:

```json
{
  "student_id": "student_001",
  "date": "2026-08-16",
  "status": "ABSENT",
  "marked_by": "teacher_001",
  "created_at": "...",
  "updated_at": "..."
}
```

## Service Methods

```python
get_student_attendance(student_id, date_range)
get_child_attendance(parent_id, child_id, date_range)
mark_attendance(teacher_id, student_id, date, status)
get_overall_attendance()
```

## Authorization

The domain service must use Section 05 policies.

Do not duplicate role logic in random route handlers.

## Tool Adapters

Implement the tools:

```text
get_own_attendance
get_child_attendance
get_overall_attendance
mark_attendance
```

## APIs

```http
GET /api/v1/attendance/student/{student_id}
POST /api/v1/attendance
GET /api/v1/attendance/analytics/overall
```

Exact exposure may be adjusted during final wiring.

## Ambiguity

If multiple students have the same name, return an ambiguity state rather than guessing.

## Acceptance Tests

- student own attendance
- parent child attendance
- teacher mark attendance
- principal analytics
- unauthorized cases
- duplicate-name handling
- missing date handling

---
