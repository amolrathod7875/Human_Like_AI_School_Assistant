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

# SECTION 05 — AUTHORIZATION ENGINE

## Assigned coder

Security / Authorization Coder

## Goal

Build the application-level authorization engine.

This is one of the most important modules.

## Core Principle

```text
Authentication = Who are you?

Authorization = What are you allowed to do?
```

## Authorization Context

Build a context containing:

```text
user_id
firebase_uid
role
relationship data
active status
```

## Policies

### STUDENT

Allowed:

```text
own attendance
own conversation
own permitted profile information
```

Denied:

```text
other student's attendance
mark attendance
school analytics
```

### PARENT

Allowed:

```text
own children attendance
child-related permitted information
child escalation
```

Denied:

```text
unrelated child data
attendance marking
principal-only analytics
```

### TEACHER

Allowed:

```text
authorized classes
authorized students
mark attendance
```

Denied:

```text
unrelated classes
unauthorized students
```

### PRINCIPAL

Allowed:

```text
school-wide attendance analytics
management-level authorized operations
```

## Policy Functions

Implement explicit functions:

```python
can_view_own_attendance(context)
can_view_child_attendance(context, child_id)
can_mark_attendance(context, student_id)
can_view_school_analytics(context)
can_create_teacher_escalation(context, student_id)
can_create_management_escalation(context)
```

## Failure Behavior

Return structured authorization failures.

Do not expose unnecessary internal relationship data.

## Acceptance Tests

Test every role against:

- allowed action
- denied action
- unrelated resource
- fake role claim
- inactive user

---
