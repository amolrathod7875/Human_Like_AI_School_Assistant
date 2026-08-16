import asyncio
import pytest
from pydantic import BaseModel

from app.ai.tools import (
    BaseTool,
    InvalidArgumentsError,
    ToolAuthorizationError,
    ToolNotFoundError,
    ToolResultValidationError,
    execute_tool,
    get_tool,
    list_tool_definitions,
    list_tools,
    register_tool,
    reset_registry,
    set_authorization_hook,
)
from app.auth.authorization.context import build_authorization_context
from app.schemas.user import Role, UserProfile


class AddArgs(BaseModel):
    a: int
    b: int


class SumOut(BaseModel):
    sum: int


class AddTool(BaseTool):
    name = "add"
    description = "Add two integers"
    input_schema = AddArgs

    async def execute(self, context, arguments):
        return {"sum": arguments.a + arguments.b}


class ValidatedTool(BaseTool):
    name = "validated"
    description = "Returns a validated sum"
    input_schema = AddArgs
    output_schema = SumOut

    async def execute(self, context, arguments):
        return {"sum": arguments.a + arguments.b}


class GuardedTool(BaseTool):
    name = "guarded"
    description = "Denies negative first argument"
    input_schema = AddArgs

    def authorize(self, context, arguments):
        if arguments.a < 0:
            raise ToolAuthorizationError("negative a not allowed")

    async def execute(self, context, arguments):
        return {"ok": True}


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    yield
    reset_registry()


def _ctx():
    return build_authorization_context(
        UserProfile(
            id="u1", firebase_uid="fb1", name="S", role=Role.STUDENT, student_id="u1"
        )
    )


def test_register_and_lookup_tool():
    register_tool(AddTool())
    tool = get_tool("add")
    assert tool is not None and tool.name == "add"
    assert any(t.name == "add" for t in list_tools())
    defs = list_tool_definitions()
    assert any(d["name"] == "add" for d in defs)


def test_unknown_tool_rejected():
    with pytest.raises(ToolNotFoundError):
        asyncio.run(execute_tool("nope", _ctx(), {"a": 1, "b": 2}))


def test_invalid_arguments_rejected():
    register_tool(AddTool())
    with pytest.raises(InvalidArgumentsError):
        asyncio.run(execute_tool("add", _ctx(), {"a": 1}))  # missing 'b'


def test_tool_execution_returns_result():
    register_tool(AddTool())
    result = asyncio.run(execute_tool("add", _ctx(), {"a": 2, "b": 3}))
    assert result == {"sum": 5}


def test_authorization_hook_denies():
    register_tool(AddTool())
    set_authorization_hook(
        lambda tool, ctx, args: (_ for _ in ()).throw(
            ToolAuthorizationError("denied by hook")
        )
    )
    with pytest.raises(ToolAuthorizationError):
        asyncio.run(execute_tool("add", _ctx(), {"a": 1, "b": 1}))


def test_tool_level_authorize_denies():
    register_tool(GuardedTool())
    with pytest.raises(ToolAuthorizationError):
        asyncio.run(execute_tool("guarded", _ctx(), {"a": -1, "b": 1}))
    # Allowed case works.
    assert asyncio.run(execute_tool("guarded", _ctx(), {"a": 1, "b": 1})) == {"ok": True}


def test_result_validation():
    register_tool(ValidatedTool())
    # Valid result passes output-schema validation.
    assert asyncio.run(execute_tool("validated", _ctx(), {"a": 1, "b": 1})) == SumOut(sum=2)

    # Break the tool to return an invalid result shape.
    class BadTool(ValidatedTool):
        async def execute(self, context, arguments):
            return {"wrong": 1}

    reset_registry()
    register_tool(BadTool())
    with pytest.raises(ToolResultValidationError):
        asyncio.run(execute_tool("validated", _ctx(), {"a": 1, "b": 1}))
