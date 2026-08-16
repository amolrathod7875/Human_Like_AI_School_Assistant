from typing import Optional

from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.ai.tools.errors import (
    InvalidArgumentsError,
    ToolAuthorizationError,
    ToolError,
)
from app.core.errors import AppError
from app.auth.authorization.context import AuthorizationContext
from app.services import escalation_service as svc
from app.services.escalation_service import (
    STATUS_CANCELLED,
    STATUS_CONFIRMED,
    STATUS_FAILED,
)


class _TeacherContactArgs(BaseModel):
    student_id: str
    reason: str = Field(min_length=1, max_length=500)
    # The human hand-off requires explicit user confirmation. The orchestrator
    # only reaches this tool after the user has asked for contact; the model must
    # confirm in the same/next turn before the request is actually dispatched.
    confirmed: bool = False


class _ManagementContactArgs(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    student_id: Optional[str] = None
    confirmed: bool = False


class CreateTeacherContactTool(BaseTool):
    name = "create_teacher_contact_request"
    description = (
        "Request human contact with a student's teacher (parent or teacher only). "
        "Requires student_id, a reason, and explicit confirmation."
    )
    input_schema = _TeacherContactArgs

    async def execute(self, context: AuthorizationContext, arguments: _TeacherContactArgs):
        if not arguments.confirmed:
            raise InvalidArgumentsError(
                "Please confirm you want to request contact with the teacher."
            )
        try:
            request = await svc.request_teacher_contact(
            context, arguments.student_id, arguments.reason
            )
        except AppError as exc:
            if exc.status_code == 403:
                raise ToolAuthorizationError(exc.message or "Forbidden")
            raise
        return _summarize(request)


class CreateManagementContactTool(BaseTool):
    name = "create_management_contact_request"
    description = (
        "Request human contact with school management (teacher or principal only). "
        "Requires a reason and explicit confirmation."
    )
    input_schema = _ManagementContactArgs

    async def execute(self, context: AuthorizationContext, arguments: _ManagementContactArgs):
        if not arguments.confirmed:
            raise InvalidArgumentsError(
                "Please confirm you want to request contact with management."
            )
        try:
            request = await svc.request_management_contact(
            context, arguments.reason, student_id=arguments.student_id
            )
        except AppError as exc:
            if exc.status_code == 403:
                raise ToolAuthorizationError(exc.message or "Forbidden")
            raise
        return _summarize(request)


def _summarize(request):
    """Return a minimal, status-bearing payload.

    The AI is allowed to say a human was contacted ONLY when status == CONFIRMED;
    the orchestrator enforces that the response text derives from this payload.
    """
    payload = {
        "request_id": request.id,
        "target_type": request.target_type,
        "status": request.status,
    }
    if request.status == STATUS_CONFIRMED:
        payload["message"] = "Your request to contact the {0} has been confirmed.".format(
            request.target_type.lower()
        )
    elif request.status == STATUS_FAILED:
        payload["message"] = "The request could not be completed. Please try again later."
    elif request.status == STATUS_CANCELLED:
        payload["message"] = "The request was cancelled."
    else:
        payload["message"] = "Your request is pending confirmation."
    return payload
