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

# SECTION 09 — AI TOOL REGISTRY

## Assigned coder

Tooling Framework Coder

## Goal

Create the standard tool framework that the AI can invoke.

## Core Interface

```python
class AITool(Protocol):
    name: str
    description: str
    input_schema: ...

    async def execute(
        self,
        context,
        arguments
    ):
        ...
```

## Tool Registry

Provide:

```python
register_tool(tool)
get_tool(name)
list_tools()
execute_tool(name, context, arguments)
```

## Execution Pipeline

```text
requested tool
   ↓
check tool exists
   ↓
validate arguments
   ↓
authorization
   ↓
execute service
   ↓
validate result
   ↓
return structured output
```

## Tool Allowlist

Only registered tools may execute.

## Important

The registry must be independent from Cohere.

The model can request a tool by name, but it cannot dynamically register or create a new tool.

## Acceptance Tests

- register tool
- lookup tool
- unknown tool rejected
- invalid arguments rejected
- tool execution
- authorization hook
- result validation

---
