from typing import List, Optional

from app.auth.authorization.context import AuthorizationContext
from app.auth.authorization.policies import (
    can_mark_attendance,
    can_view_child_attendance,
    can_view_own_attendance,
    can_view_school_analytics,
    enforce,
)
from app.core.errors import AppError
from app.repositories import AttendanceRepository, StudentRepository
from app.repositories.base import Page
from app.schemas.attendance import (
    AttendanceStatus,
    AttendanceSummary,
    DateRange,
    StudentAmbiguity,
    StudentCandidate,
)
from app.schemas.collections import AttendanceRecord

# Dependency injection points (overridden by tests).
_attendance_repo: Optional[AttendanceRepository] = None
_student_repo: Optional[StudentRepository] = None


def set_attendance_repository(repo: Optional[AttendanceRepository]) -> None:
    global _attendance_repo
    _attendance_repo = repo


def get_attendance_repository() -> AttendanceRepository:
    global _attendance_repo
    if _attendance_repo is None:
        _attendance_repo = AttendanceRepository()
    return _attendance_repo


def set_student_repository(repo: Optional[StudentRepository]) -> None:
    global _student_repo
    _student_repo = repo


def get_student_repository() -> StudentRepository:
    global _student_repo
    if _student_repo is None:
        _student_repo = StudentRepository()
    return _student_repo


def _range_filters(date_range: Optional[DateRange]):
    start = date_range.start_date if date_range else None
    end = date_range.end_date if date_range else None
    return start, end


# ---------------- Name / id resolution ----------------
def resolve_student_reference(
    *, name: Optional[str] = None, student_id: Optional[str] = None
) -> StudentAmbiguity:
    """Resolve a student reference to a single id.

    If a name matches multiple students, returns `ambiguous=True` with the
    candidate list so callers never guess which student was meant.
    """
    if student_id:
        return StudentAmbiguity(resolved_id=student_id)

    if not name:
        return StudentAmbiguity()  # neither supplied -> unresolved

    matches = get_student_repository().list_by_name(name, page_size=50).items
    if not matches:
        return StudentAmbiguity()
    if len(matches) > 1:
        return StudentAmbiguity(
            ambiguous=True,
            candidates=[
                StudentCandidate(
                    student_id=s.id, name=s.name, class_id=s.class_id
                )
                for s in matches
            ],
        )
    return StudentAmbiguity(resolved_id=matches[0].id)


# ---------------- Read: student own ----------------
def get_student_attendance(
    context: AuthorizationContext,
    student_id: str,
    date_range: Optional[DateRange] = None,
) -> List[AttendanceRecord]:
    # A student may only read their own record; parents/teachers use the
    # dedicated child/authorized paths. Anything else is denied.
    if context.role.value == "STUDENT":
        enforce(can_view_own_attendance(context))
        if student_id != context.relationship.student_id:
            raise AppError(
                "Students may only view their own attendance",
                "FORBIDDEN",
                status_code=403,
            )
    elif context.role.value == "PARENT":
        enforce(can_view_child_attendance(context, student_id))
    else:
        raise AppError(
            "Not authorized to view this student's attendance",
            "FORBIDDEN",
            status_code=403,
        )

    start, end = _range_filters(date_range)
    page = get_attendance_repository().list_by_student_range(
        student_id, start_date=start, end_date=end, page_size=500
    )
    return page.items


# ---------------- Read: parent -> child ----------------
def get_child_attendance(
    context: AuthorizationContext,
    child_id: str,
    date_range: Optional[DateRange] = None,
) -> List[AttendanceRecord]:
    # parent_id is taken from the stored identity, never the caller's input.
    enforce(can_view_child_attendance(context, child_id))

    start, end = _range_filters(date_range)
    page = get_attendance_repository().list_by_student_range(
        child_id, start_date=start, end_date=end, page_size=500
    )
    return page.items


# ---------------- Write: teacher marks attendance ----------------
def mark_attendance(
    context: AuthorizationContext,
    student_id: str,
    date: str,
    status: AttendanceStatus,
) -> AttendanceRecord:
    # teacher_id comes strictly from the stored identity (rule 10). The plan's
    # teacher_id parameter is intentionally ignored for authorization.
    enforce(can_mark_attendance(context, student_id))

    student = get_student_repository().get(student_id)
    if student is None:
        raise AppError("Student not found", "NOT_FOUND", status_code=404)

    repo = get_attendance_repository()
    existing = repo.get_by_student_and_date(student_id, date)
    if existing is not None:
        repo.update(
            existing.id,
            {"status": status.value, "marked_by": context.user_id},
        )
        return AttendanceRecord(
            **{
                **existing.model_dump(exclude={"id"}),
                "id": existing.id,
                "status": status.value,
                "marked_by": context.user_id,
            }
        )

    record = AttendanceRecord(
        id="",
        student_id=student_id,
        class_id=student.class_id or "",
        date=date,
        status=status.value,
        marked_by=context.user_id,
    )
    return repo.create(record)


# ---------------- Read: principal analytics ----------------
def get_overall_attendance(
    context: AuthorizationContext, date_range: Optional[DateRange] = None
) -> AttendanceSummary:
    enforce(can_view_school_analytics(context))

    start, end = _range_filters(date_range)
    present = absent = late = total = 0
    repo = get_attendance_repository()
    # Stream all matching records and aggregate counts.
    page: Page[AttendanceRecord] = repo.list_all(page_size=500)
    while True:
        for rec in page.items:
            if start is not None and rec.date < start:
                continue
            if end is not None and rec.date > end:
                continue
            total += 1
            if rec.status == AttendanceStatus.PRESENT.value:
                present += 1
            elif rec.status == AttendanceStatus.ABSENT.value:
                absent += 1
            elif rec.status == AttendanceStatus.LATE.value:
                late += 1
        if page.next_page_token is None:
            break
        page = repo.list_all(page_size=500, start_after=page.next_page_token)

    rate = (present / total * 100.0) if total else 0.0
    return AttendanceSummary(
        total=total,
        present=present,
        absent=absent,
        late=late,
        attendance_rate=round(rate, 2),
    )
