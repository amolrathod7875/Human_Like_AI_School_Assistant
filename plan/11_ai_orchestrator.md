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

# SECTION 11 — AI ORCHESTRATOR

## Assigned coder

AI Agent / Orchestration Coder

## Goal

Build the central natural-language workflow.

## Input

```json
{
  "conversation_id": "conv_001",
  "message": "How much attendance does my child have?"
}
```

User identity comes from authenticated backend context.

## Processing Flow

```text
1. authenticate
2. load user profile
3. load role
4. load conversation
5. load language
6. load persona
7. give context to Cohere
8. determine intent / tool need
9. validate model output
10. call registered tool if needed
11. authorization happens
12. tool executes
13. send result back to Cohere
14. create natural response
15. persist messages
16. return structured response
```

## Intents

At minimum:

```text
VIEW_OWN_ATTENDANCE
VIEW_CHILD_ATTENDANCE
MARK_ATTENDANCE
VIEW_SCHOOL_ATTENDANCE
REQUEST_TEACHER_CONTACT
REQUEST_MANAGEMENT_CONTACT
GENERAL_QUERY
```

## Entity Extraction

At minimum:

```text
student_name
student_id
date
date_range
class_id
reason
```

## Missing Information

Example:

```text
Mark Rahul absent.
```

If Rahul cannot be uniquely resolved:

```text
Please clarify which Rahul you mean.
```

Do not guess.

## Response Contract

```json
{
  "conversation_id": "...",
  "message_id": "...",
  "text": "...",
  "language": "en-IN",
  "persona": "parent",
  "tool_calls": [],
  "avatar": {
    "state": "speaking",
    "emotion": "friendly"
  }
}
```

## Important

The orchestrator is not the authorization engine.

It must call authorization/tool infrastructure.

---
