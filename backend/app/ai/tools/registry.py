from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ValidationError

from app.ai.tools.base import AITool
from app.ai.tools.errors import (
    InvalidArgumentsError,
    ToolAuthorizationError,
    ToolError,
    ToolNotFoundError,
    ToolResultValidationError,
)
from app.auth.authorization.context import AuthorizationContext

# Registry state. The set of registered tools is the allowlist: only registered
# tools can be executed, and the LLM cannot register new ones at runtime.
_tools: Dict[str, AITool] = {}
_authorizer: Optional[Callable[[AITool, AuthorizationContext, BaseModel], None]] = None


def register_tool(tool: AITool) -> None:
    """Register a tool by its `name` (overwrites on duplicate)."""
    _tools[tool.name] = tool


def get_tool(name: str) -> Optional[AITool]:
    return _tools.get(name)


def list_tools() -> List[AITool]:
    return list(_tools.values())


def list_tool_definitions() -> List[dict]:
    """Provider-agnostic tool definitions for the orchestrator to wire into an LLM."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema.model_json_schema(),
        }
        for tool in _tools.values()
    ]


def set_authorization_hook(
    hook: Optional[Callable[[AITool, AuthorizationContext, BaseModel], None]],
) -> None:
    """Set a registry-wide authorization hook. `None` clears it (permissive)."""
    global _authorizer
    _authorizer = hook


async def execute_tool(
    name: str,
    context: AuthorizationContext,
    arguments: Any,
    authorizer: Optional[Callable[[AITool, AuthorizationContext, BaseModel], None]] = None,
) -> Any:
    """Run the full tool-execution pipeline.

    Pipeline: exists -> validate arguments -> authorize -> execute -> validate result.
    """
    tool = get_tool(name)
    if tool is None:
        raise ToolNotFoundError(f"Unknown tool: {name}")

    try:
        validated = tool.input_schema.model_validate(arguments)
    except ValidationError as exc:
        raise InvalidArgumentsError(
            f"Invalid arguments for tool '{name}': {exc}"
        ) from exc

    # Authorization: registry hook (if set) then tool-level authorize().
    authz = authorizer or _authorizer
    if authz is not None:
        authz(tool, context, validated)
    authorize = getattr(tool, "authorize", None)
    if callable(authorize):
        authorize(context, validated)

    # Execute the underlying service. Only ToolError propagates as-is; other
    # exceptions are wrapped so the failure stays within the tool framework.
    try:
        result = await tool.execute(context, validated)
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Tool '{name}' execution failed: {exc}") from exc

    # Result validation (optional per tool).
    output_schema = getattr(tool, "output_schema", None)
    if output_schema is not None:
        try:
            result = output_schema.model_validate(result)
        except ValidationError as exc:
            raise ToolResultValidationError(
                f"Tool '{name}' returned an invalid result: {exc}"
            ) from exc

    return result


def reset_registry() -> None:
    """Clear all tools and the authorization hook (used by tests)."""
    _tools.clear()
    set_authorization_hook(None)
