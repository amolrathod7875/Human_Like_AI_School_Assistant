from typing import Optional

from pydantic import BaseModel

from app.ai.tools.base import BaseTool
from app.ai.tools.errors import (
    InvalidArgumentsError,
    ToolAuthorizationError,
    ToolError,
)
from app.auth.authorization.context import AuthorizationContext
from app.auth.authorization.policies import (
    can_mark_attendance,
    can_view_child_attendance,
    can_view_own_attendance,
    can_view_school_analytics,
)
from app.schemas.attendance import AttendanceStatus, DateRange, MarkAttendanceInput
from app.services.attendance_service import (
    get_child_attendance,
    get_overall_attendance,
    get_student_attendance,
    mark_attendance,
    resolve_student_reference,
)


def _deny(result):
    if not result.allowed:
        raise ToolAuthorizationError(result.message or "Forbidden")


def _resolve_student(args) -> str:
    """Resolve name/id to a single student id or raise a clear tool error.

    Never guesses when a name is ambiguous.
    """
    amb = resolve_student_reference(name=getattr(args, "name", None),
                                    student_id=getattr(args, "student_id", None))
    if amb.ambiguous:
        names = ", ".join(
            f"{c.name} ({c.student_id})" for c in amb.candidates
        )
        raise InvalidArgumentsError(
            f"Multiple students match that name: {names}. Please specify which one."
        )
    if not amb.resolved_id:
        raise InvalidArgumentsError("No student found for the given name/id.")
    return amb.resolved_id


class _ChildAttendanceArgs(BaseModel):
    student_id: Optional[str] = None
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class GetOwnAttendanceTool(BaseTool):
    name = "get_own_attendance"
    description = "View the calling student's own attendance records."
    input_schema = DateRange

    def authorize(self, context: AuthorizationContext, arguments: DateRange) -> None:
        _deny(can_view_own_attendance(context))

    async def execute(self, context: AuthorizationContext, arguments: DateRange):
        return get_student_attendance(
            context, context.relationship.student_id, date_range=arguments
        )


class GetChildAttendanceTool(BaseTool):
    name = "get_child_attendance"
    description = (
        "View a parent's child attendance records. Provide student_id or name."
    )
    input_schema = _ChildAttendanceArgs

    def authorize(self, context: AuthorizationContext, arguments: _ChildAttendanceArgs) -> None:
        student_id = _resolve_student(arguments)
        _deny(can_view_child_attendance(context, student_id))

    async def execute(self, context: AuthorizationContext, arguments: _ChildAttendanceArgs):
        student_id = _resolve_student(arguments)
        rng = DateRange(start_date=arguments.start_date, end_date=arguments.end_date)
        return get_child_attendance(context, student_id, date_range=rng)


class GetOverallAttendanceTool(BaseTool):
    name = "get_overall_attendance"
    description = "View school-wide attendance analytics (principal only)."
    input_schema = DateRange

    def authorize(self, context: AuthorizationContext, arguments: DateRange) -> None:
        _deny(can_view_school_analytics(context))

    async def execute(self, context: AuthorizationContext, arguments: DateRange):
        return get_overall_attendance(context, date_range=arguments)


class MarkAttendanceTool(BaseTool):
    name = "mark_attendance"
    description = (
        "Mark a student's attendance (PRESENT/ABSENT/LATE) for a date. "
        "Teacher only; provide student_id or name."
    )
    input_schema = MarkAttendanceInput

    def authorize(self, context: AuthorizationContext, arguments: MarkAttendanceInput) -> None:
        student_id = _resolve_student(arguments)
        _deny(can_mark_attendance(context, student_id))

    async def execute(self, context: AuthorizationContext, arguments: MarkAttendanceInput):
        student_id = _resolve_student(arguments)
        return mark_attendance(
            context, student_id, arguments.date, arguments.status
        )
