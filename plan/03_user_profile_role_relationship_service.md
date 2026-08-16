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

# SECTION 03 — USER PROFILE / ROLE / RELATIONSHIP SERVICE

## Assigned coder

Identity and School Relationship Coder

## Goal

Create application-level user profiles and role relationships.

## Roles

```text
STUDENT
PARENT
TEACHER
PRINCIPAL
```

## Firestore

Collection:

```text
users
```

Example:

```json
{
  "firebase_uid": "firebase-123",
  "name": "Amit Sharma",
  "email": "amit@example.com",
  "role": "PARENT",
  "student_id": null,
  "child_ids": ["student_001"],
  "teacher_class_ids": [],
  "is_active": true
}
```

## Relationships

Student:

```text
student_id
parent_ids
class_id
```

Parent:

```text
child_ids
```

Teacher:

```text
class_ids
```

Principal:

```text
school-wide access
```

## Service Interface

Implement:

```python
get_user_by_firebase_uid(firebase_uid)
get_user_by_id(user_id)
get_user_role(user_id)
get_children_for_parent(parent_id)
get_teacher_classes(teacher_id)
is_active_user(user_id)
```

## Critical Rule

Do not trust role from:

- frontend
- query parameter
- request body
- LLM
- tool arguments

Only Firestore/application identity is authoritative.

## Acceptance Tests

- each role loads correctly
- parent-child relationship resolves
- teacher-class relationship resolves
- inactive user is rejected
- fake role value does not override stored role

---
