from app.auth.authorization.context import (
    AuthorizationContext,
    AuthorizationResult,
)
from app.core.errors import AppError
from app.schemas.user import Role


def _allow() -> AuthorizationResult:
    return AuthorizationResult(allowed=True)


def _deny(code: str, message: str) -> AuthorizationResult:
    # Deliberately generic message: do not leak relationship internals.
    return AuthorizationResult(allowed=False, code=code, message=message)


def enforce(result: AuthorizationResult) -> None:
    """Raise a standardized 403 when a policy check fails.

    Use inside route handlers / services after calling a policy function.
    """
    if not result.allowed:
        raise AppError(
            result.message or "Forbidden", "FORBIDDEN", status_code=403
        )


def can_view_own_attendance(context: AuthorizationContext) -> AuthorizationResult:
    if not context.active:
        return _deny("INACTIVE_USER", "User is not active")
    if context.role != Role.STUDENT:
        return _deny("ROLE_NOT_ALLOWED", "Action not allowed for this role")
    return _allow()


def can_view_child_attendance(
    context: AuthorizationContext, child_id: str
) -> AuthorizationResult:
    if not context.active:
        return _deny("INACTIVE_USER", "User is not active")
    if context.role != Role.PARENT:
        return _deny("ROLE_NOT_ALLOWED", "Action not allowed for this role")
    if child_id not in context.relationship.child_ids:
        return _deny("NOT_YOUR_CHILD", "Not authorized for the requested child")
    return _allow()


def can_mark_attendance(
    context: AuthorizationContext, student_id: str
) -> AuthorizationResult:
    if not context.active:
        return _deny("INACTIVE_USER", "User is not active")
    if context.role != Role.TEACHER:
        return _deny("ROLE_NOT_ALLOWED", "Action not allowed for this role")
    if student_id not in context.relationship.authorized_student_ids:
        return _deny("NOT_YOUR_STUDENT", "Student not in your authorized classes")
    return _allow()


def can_view_school_analytics(
    context: AuthorizationContext,
) -> AuthorizationResult:
    if not context.active:
        return _deny("INACTIVE_USER", "User is not active")
    if context.role != Role.PRINCIPAL:
        return _deny("ROLE_NOT_ALLOWED", "Action not allowed for this role")
    return _allow()


def can_create_teacher_escalation(
    context: AuthorizationContext, student_id: str
) -> AuthorizationResult:
    if not context.active:
        return _deny("INACTIVE_USER", "User is not active")
    if context.role != Role.TEACHER:
        return _deny("ROLE_NOT_ALLOWED", "Action not allowed for this role")
    if student_id not in context.relationship.authorized_student_ids:
        return _deny("NOT_YOUR_STUDENT", "Student not in your authorized classes")
    return _allow()


def can_create_management_escalation(
    context: AuthorizationContext,
) -> AuthorizationResult:
    if not context.active:
        return _deny("INACTIVE_USER", "User is not active")
    if context.role != Role.PRINCIPAL:
        return _deny("ROLE_NOT_ALLOWED", "Action not allowed for this role")
    return _allow()
