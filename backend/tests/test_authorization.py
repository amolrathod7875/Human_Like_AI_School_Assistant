import pytest

from app.auth.authorization.context import (
    AuthorizationContext,
    build_authorization_context,
    get_authorization_context,
)
from app.auth.authorization.policies import (
    can_create_management_escalation,
    can_create_teacher_escalation,
    can_mark_attendance,
    can_view_child_attendance,
    can_view_own_attendance,
    can_view_school_analytics,
    enforce,
)
from app.auth.context import AuthenticatedUser
from app.core.errors import AppError
from app.repositories.base import Page
from app.repositories.user_repository import set_user_repository
from app.schemas.collections import StudentProfile
from app.schemas.user import Role, UserProfile


class FakeStudentRepo:
    def __init__(self, by_class):
        self._by_class = by_class

    def list_by_class(self, class_id, **kwargs):
        ids = self._by_class.get(class_id, [])
        items = [
            StudentProfile(id=i, user_id=i, name=i, class_id=class_id)
            for i in ids
        ]
        return Page(items=items)


class FakeUserRepository:
    def __init__(self, by_uid=None):
        self._by_uid = by_uid or {}

    def get_by_id(self, user_id):
        return None

    def get_by_firebase_uid(self, firebase_uid):
        return self._by_uid.get(firebase_uid)


def student_context(active=True):
    return build_authorization_context(
        UserProfile(
            id="s1",
            firebase_uid="fbs",
            name="Stu",
            role=Role.STUDENT,
            is_active=active,
            student_id="s1",
        )
    )


def parent_context(active=True, child_ids=None):
    return build_authorization_context(
        UserProfile(
            id="p1",
            firebase_uid="fbp",
            name="Par",
            role=Role.PARENT,
            is_active=active,
            child_ids=child_ids or ["c1"],
        )
    )


def teacher_context(active=True, by_class=None):
    return build_authorization_context(
        UserProfile(
            id="t1",
            firebase_uid="fbt",
            name="Tea",
            role=Role.TEACHER,
            is_active=active,
            teacher_class_ids=["c1"],
        ),
        student_repo=FakeStudentRepo(by_class or {"c1": ["s1", "s2"]}),
    )


def principal_context(active=True):
    return build_authorization_context(
        UserProfile(
            id="pr1", firebase_uid="fbpr", name="Pri", role=Role.PRINCIPAL,
            is_active=active,
        )
    )


# ---------------- STUDENT ----------------
def test_student_own_attendance_allowed():
    assert can_view_own_attendance(student_context()).allowed is True


def test_student_cannot_view_child_attendance():
    assert can_view_child_attendance(student_context(), "c1").allowed is False


def test_student_cannot_mark_attendance():
    assert can_mark_attendance(student_context(), "s1").allowed is False


def test_student_cannot_view_analytics():
    assert can_view_school_analytics(student_context()).allowed is False


def test_inactive_student_denied():
    res = can_view_own_attendance(student_context(active=False))
    assert res.allowed is False and res.code == "INACTIVE_USER"


# ---------------- PARENT ----------------
def test_parent_can_view_own_child():
    assert can_view_child_attendance(parent_context(), "c1").allowed is True


def test_parent_cannot_view_unrelated_child():
    res = can_view_child_attendance(parent_context(), "cx")
    assert res.allowed is False and res.code == "NOT_YOUR_CHILD"


def test_parent_cannot_mark_attendance():
    assert can_mark_attendance(parent_context(), "s1").allowed is False


def test_parent_cannot_view_analytics():
    assert can_view_school_analytics(parent_context()).allowed is False


def test_inactive_parent_denied():
    res = can_view_child_attendance(parent_context(active=False), "c1")
    assert res.allowed is False and res.code == "INACTIVE_USER"


# ---------------- TEACHER ----------------
def test_teacher_can_mark_authorized_student():
    assert can_mark_attendance(teacher_context(), "s1").allowed is True


def test_teacher_cannot_mark_unauthorized_student():
    res = can_mark_attendance(teacher_context(), "s9")
    assert res.allowed is False and res.code == "NOT_YOUR_STUDENT"


def test_teacher_can_escalate_authorized_student():
    assert can_create_teacher_escalation(teacher_context(), "s2").allowed is True


def test_teacher_cannot_view_own_attendance():
    assert can_view_own_attendance(teacher_context()).allowed is False


def test_teacher_cannot_view_analytics():
    assert can_view_school_analytics(teacher_context()).allowed is False


def test_inactive_teacher_denied():
    res = can_mark_attendance(teacher_context(active=False), "s1")
    assert res.allowed is False and res.code == "INACTIVE_USER"


# ---------------- PRINCIPAL ----------------
def test_principal_can_view_analytics():
    assert can_view_school_analytics(principal_context()).allowed is True


def test_principal_can_management_escalation():
    assert can_create_management_escalation(principal_context()).allowed is True


def test_principal_cannot_mark_attendance():
    assert can_mark_attendance(principal_context(), "s1").allowed is False


def test_principal_cannot_view_child_attendance():
    assert can_view_child_attendance(principal_context(), "c1").allowed is False


def test_inactive_principal_denied():
    res = can_view_school_analytics(principal_context(active=False))
    assert res.allowed is False and res.code == "INACTIVE_USER"


# ---------------- Fake role claim ----------------
def test_fake_role_claim_does_not_grant_access():
    # A context built from a stored STUDENT profile (the only authoritative
    # source) can never satisfy a principal-only policy, regardless of what a
    # client might claim in a token.
    assert can_view_school_analytics(student_context()).allowed is False
    assert can_mark_attendance(parent_context(), "s1").allowed is False
    assert can_view_child_attendance(teacher_context(), "c1").allowed is False


# ---------------- Context builder ----------------
def test_context_relationship_scoping():
    assert student_context().relationship.student_id == "s1"
    assert parent_context().relationship.child_ids == ["c1"]
    assert teacher_context().relationship.authorized_student_ids == ["s1", "s2"]
    assert teacher_context().relationship.class_ids == ["c1"]
    assert principal_context().relationship.school_wide is True


# ---------------- enforce() ----------------
def test_enforce_passes_when_allowed():
    assert enforce(can_view_own_attendance(student_context())) is None


def test_enforce_raises_forbidden():
    with pytest.raises(AppError) as exc:
        enforce(can_view_school_analytics(student_context()))
    assert exc.value.code == "FORBIDDEN"
    assert exc.value.status_code == 403


# ---------------- Loader uses stored identity ----------------
def test_get_authorization_context_uses_stored_profile():
    set_user_repository(
        FakeUserRepository(
            by_uid={"fb1": UserProfile(id="p1", firebase_uid="fb1", name="Par",
                                       role=Role.PARENT, child_ids=["c1"])}
        )
    )
    ctx = get_authorization_context(AuthenticatedUser(firebase_uid="fb1"))
    assert isinstance(ctx, AuthorizationContext)
    assert ctx.role == Role.PARENT
    set_user_repository(None)


def test_get_authorization_context_missing_profile_is_forbidden():
    set_user_repository(FakeUserRepository())
    with pytest.raises(AppError) as exc:
        get_authorization_context(AuthenticatedUser(firebase_uid="missing"))
    assert exc.value.code == "FORBIDDEN"
    set_user_repository(None)
