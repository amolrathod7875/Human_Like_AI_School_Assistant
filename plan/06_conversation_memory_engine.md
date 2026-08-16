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

# SECTION 06 — CONVERSATION + MEMORY ENGINE

## Assigned coder

Conversation Systems Coder

## Goal

Store conversations and make context available to the AI orchestrator.

## Firestore

```text
conversations
messages
```

A message may be represented as a nested subcollection:

```text
conversations/{conversationId}/messages/{messageId}
```

## Conversation Schema

```json
{
  "conversation_id": "conv_001",
  "user_id": "user_001",
  "role": "PARENT",
  "language": "en-IN",
  "created_at": "...",
  "updated_at": "...",
  "metadata": {}
}
```

## Message Schema

```json
{
  "message_id": "msg_001",
  "role": "user",
  "content": "How much attendance does Rahul have?",
  "timestamp": "...",
  "intent": "VIEW_CHILD_ATTENDANCE",
  "entities": {
    "student_name": "Rahul"
  },
  "tool_calls": [],
  "tool_results": []
}
```

## Required Service

```python
create_conversation()
get_conversation()
append_message()
get_recent_messages()
build_context()
```

## Context Output

The orchestrator should receive something like:

```python
ConversationContext(
    conversation_id,
    recent_messages,
    language,
    known_entities,
    previous_tool_results
)
```

## Follow-Up Requirement

Support:

```text
User: How much attendance does Rahul have?
AI: Rahul has 91.2%.
User: What about last month?
```

The second message must be able to use existing context.

## Security

A user must only access their own conversations unless an explicit administrative policy exists.

## Acceptance Tests

- create conversation
- append messages
- retrieve recent messages
- ownership enforcement
- context generation
- follow-up context test

---
