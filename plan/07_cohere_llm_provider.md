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

# SECTION 07 — COHERE LLM PROVIDER

## Assigned coder

LLM Integration Coder

## Goal

Create a clean Cohere provider layer.

## In Scope

- Cohere SDK/client
- model configuration
- API wrapper
- timeouts
- errors
- retry behavior where safe
- structured model output handling
- test mock provider

## Interface

Define a generic interface such as:

```python
class LLMProvider(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...
```

## Request

Include:

```text
system instructions
conversation messages
user context allowed for prompting
tool definitions if used
language instruction
persona instruction
```

Do NOT include secrets.

## Response

Normalize provider-specific output into an application format:

```python
LLMResponse(
    text=...,
    tool_calls=[...],
    finish_reason=...
)
```

## Provider Independence

The rest of the project should not import the Cohere SDK directly.

Only this provider layer should do so.

## Acceptance Tests

- provider initializes
- successful generation
- API failure
- timeout
- malformed response
- mocked generation for unit tests

---
