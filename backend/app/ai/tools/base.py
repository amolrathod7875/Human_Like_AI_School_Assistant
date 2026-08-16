from abc import ABC, abstractmethod
from typing import Any, Optional, Protocol, Type, runtime_checkable

from pydantic import BaseModel

from app.auth.authorization.context import AuthorizationContext


@runtime_checkable
class AITool(Protocol):
    """Contract every AI tool must satisfy.

    The registry is provider-agnostic (independent of Cohere). Tools receive
    the caller's `AuthorizationContext` and validated arguments.
    """

    name: str
    description: str
    input_schema: Type[BaseModel]

    async def execute(self, context: AuthorizationContext, arguments: BaseModel) -> Any:
        ...


class BaseTool(ABC):
    """Convenience base class for tools.

    Subclasses set `name`, `description`, `input_schema`, and implement
    `execute`. Optionally set `output_schema` for result validation and override
    `authorize` for tool-specific authorization checks.
    """

    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Optional[Type[BaseModel]] = None

    def authorize(self, context: AuthorizationContext, arguments: BaseModel) -> None:
        """Raise `ToolAuthorizationError` to deny. Default: allow."""
        return None

    @abstractmethod
    async def execute(self, context: AuthorizationContext, arguments: BaseModel) -> Any:
        ...
