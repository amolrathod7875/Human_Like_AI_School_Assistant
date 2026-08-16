from app.ai.tools.attendance_tools import (
    GetChildAttendanceTool,
    GetOverallAttendanceTool,
    GetOwnAttendanceTool,
    MarkAttendanceTool,
)
from app.ai.tools.registry import register_tool, reset_registry


def register_attendance_tools() -> None:
    register_tool(GetOwnAttendanceTool())
    register_tool(GetChildAttendanceTool())
    register_tool(GetOverallAttendanceTool())
    register_tool(MarkAttendanceTool())


def bootstrap_tools() -> None:
    """Register all built-in tools. Called once at app startup."""
    reset_registry()
    register_attendance_tools()
