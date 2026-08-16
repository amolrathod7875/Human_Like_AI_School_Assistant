from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.auth.authorization.context import (
    AuthorizationContext,
    get_authorization_context,
)
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_authenticated_user
from app.core.responses import ApiResponse, success_response
from app.schemas.attendance import AttendanceStatus, MarkAttendanceInput
from app.schemas.collections import AttendanceRecord
from app.services.attendance_service import (
    get_child_attendance,
    get_overall_attendance,
    get_student_attendance,
    mark_attendance,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


async def get_auth_context(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> AuthorizationContext:
    """Resolve the caller's authorization context from the verified token.

    Role/active/relationship come strictly from the stored Firestore profile.
    """
    return get_authorization_context(user)


@router.get(
    "/student/{student_id}",
    response_model=ApiResponse[List[AttendanceRecord]],
)
async def attendance_for_student(
    student_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    context: AuthorizationContext = Depends(get_auth_context),
) -> ApiResponse[List[AttendanceRecord]]:
    records = get_student_attendance(
        context, student_id, date_range=_range(start_date, end_date)
    )
    return success_response(records)


@router.post("", response_model=ApiResponse[AttendanceRecord])
async def mark_student_attendance(
    payload: MarkAttendanceInput,
    context: AuthorizationContext = Depends(get_auth_context),
) -> ApiResponse[AttendanceRecord]:
    record = mark_attendance(
        context, payload.student_id, payload.date, payload.status
    )
    return success_response(record)


@router.get(
    "/analytics/overall",
    response_model=ApiResponse[dict],
)
async def overall_attendance(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    context: AuthorizationContext = Depends(get_auth_context),
) -> ApiResponse[dict]:
    summary = get_overall_attendance(
        context, date_range=_range(start_date, end_date)
    )
    return success_response(summary.model_dump(mode="json"))


def _range(start_date, end_date):
    from app.schemas.attendance import DateRange

    return DateRange(start_date=start_date, end_date=end_date)
