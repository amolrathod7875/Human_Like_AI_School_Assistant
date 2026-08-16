class ToolError(Exception):
    """Base error for the AI tool framework."""


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not registered."""


class InvalidArgumentsError(ToolError):
    """Raised when tool arguments fail input-schema validation."""


class ToolAuthorizationError(ToolError):
    """Raised when a tool call is not authorized for the caller/context."""


class ToolResultValidationError(ToolError):
    """Raised when a tool's result fails output-schema validation."""
