# Section 09 — AI Tool Registry

Standard, provider-independent framework the AI can invoke. It is **independent
of Cohere** (no SDK import here); the orchestrator wires `list_tool_definitions()`
into whatever LLM it uses. The LLM may *request* a tool by name but cannot
register or create tools — only code registers them, and the registered set is
the allowlist.

## Interface (`app.ai.tools.base`)

```python
class AITool(Protocol):
    name: str
    description: str
    input_schema: Type[BaseModel]            # Pydantic argument schema

    async def execute(self, context, arguments): ...

class BaseTool(ABC):   # convenience base
    # optional: output_schema, override authorize(context, args)
```

`context` is the caller's `AuthorizationContext` (Section 05).

## Registry (`app.ai.tools.registry`)

```python
register_tool(tool)
get_tool(name)
list_tools()
list_tool_definitions()     # provider-agnostic {name, description, parameters}
execute_tool(name, context, arguments, authorizer=None)
set_authorization_hook(fn)  # registry-wide authorization hook
```

## Execution pipeline (`execute_tool`)

```
requested tool
  → check tool exists            (else ToolNotFoundError)
  → validate arguments           (else InvalidArgumentsError)
  → authorization                (registry hook + tool.authorize → ToolAuthorizationError)
  → execute service              (ToolError propagated; others wrapped)
  → validate result              (if output_schema set → ToolResultValidationError)
  → return structured output
```

Only registered tools execute (allowlist). Failed steps raise typed `ToolError`
subclasses so the orchestrator can map them to a safe, structured response.

## Errors

`ToolError` (base), `ToolNotFoundError`, `InvalidArgumentsError`,
`ToolAuthorizationError`, `ToolResultValidationError`.

## Usage

```python
from app.ai.tools import BaseTool, register_tool, execute_tool

class MyTool(BaseTool):
    name = "attendance_view"
    description = "..."
    input_schema = MyArgs
    output_schema = MyResult

    def authorize(self, context, args): ...        # optional
    async def execute(self, context, args): ...

register_tool(MyTool())
result = await execute_tool("attendance_view", context, {"student": "Rahul"})
```

## Tests
`tests/test_ai_tool_registry.py` covers: register/lookup, unknown tool rejected,
invalid arguments rejected, successful execution, authorization (both registry
hook and tool-level `authorize`), and output result validation.
