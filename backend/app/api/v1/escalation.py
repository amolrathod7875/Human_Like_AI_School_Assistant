from enum import Enum
from pydantic import BaseModel
from typing import Literal, Optional

from fastapi import APIRouter, Depends

from app.auth.authorization.context import (
    AuthorizationContext,
    get_authorization_context,
)
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_authenticated_user
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.responses import ApiResponse, success_response
from app.schemas.user import Role
from app.services import escalation_service as svc

logger = get_logger("app.api.v1.escalation")

router = APIRouter(prefix="/escalation", tags=["escalation"])


class TargetType(str, Enum):
    TEACHER = "TEACHER"
    MANAGEMENT = "MANAGEMENT"


class EscalationRequest(BaseModel):
    target_type: TargetType
    reason: str
    student_id: Optional[str] = None


@router.post("/request", response_model=ApiResponse[dict])
async def create_escalation(
    payload: EscalationRequest,
    context: AuthorizationContext = Depends(get_authorization_context),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ApiResponse[dict]:
    """Create a human-support escalation request.

    Parent -> teacher, Teacher/Principal -> management. Authorization is enforced
    in the escalation service (Section 05 policies); this route only validates
    the shape and dispatches.
    """
    target = payload.target_type.value
    if target == TargetType.TEACHER.value:
        if not payload.student_id:
            raise AppError("student_id is required for teacher contact",
                           "VALIDATION_ERROR", status_code=422)
        request = await svc.request_teacher_contact(
            context, payload.student_id, payload.reason
        )
    elif target == TargetType.MANAGEMENT.value:
        request = await svc.request_management_contact(
            context, payload.reason, student_id=payload.student_id
        )
    else:
        raise AppError("Unsupported target_type", "VALIDATION_ERROR", status_code=422)

    return success_response(_public(request))


@router.get("/{request_id}", response_model=ApiResponse[dict])
async def get_escalation(
    request_id: str,
    context: AuthorizationContext = Depends(get_authorization_context),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ApiResponse[dict]:
    request = await svc.get_request(request_id, context)
    return success_response(_public(request))


def _public(request):
    return {
        "request_id": request.id,
        "requested_by": request.requested_by,
        "requester_role": request.requester_role,
        "target_type": request.target_type,
        "target_id": request.target_id,
        "student_id": request.student_id,
        "reason": request.reason,
        "status": request.status,
    }
