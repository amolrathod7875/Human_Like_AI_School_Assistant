import pytest
from pydantic import ValidationError

from app.auth.authorization.context import build_authorization_context
from app.core.errors import AppError
from app.repositories.base import Page
from app.schemas.attendance import AttendanceStatus
from app.schemas.collections import AttendanceRecord, StudentProfile
from app.schemas.user import Role, UserProfile
from app.services import attendance_service as svc


class FakeAttendanceRepo:
    def __init__(self):
        self.store = {}
        self.counter = 0

    def create(self, model):
        self.counter += 1
        mid = model.id or f"a{self.counter}"
        rec = model.model_copy(update={"id": mid})
        self.store[mid] = rec
        return rec

    def get(self, doc_id):
        return self.store.get(doc_id)

    def update(self, doc_id, changes):
        self.store[doc_id] = self.store[doc_id].model_copy(update=changes)

    def list(self, *, filters=None, order_by=None, desc=False, page_size=20, start_after=None):
        items = list(self.store.values())
        for f in filters or []:
            field, op, val = f
            if op == "==":
                items = [i for i in items if getattr(i, field) == val]
            elif op == ">=":
                items = [i for i in items if getattr(i, field) >= val]
            elif op == "<=":
                items = [i for i in items if getattr(i, field) <= val]
        if order_by:
            items.sort(key=lambda i: getattr(i, order_by), reverse=desc)
        if start_after:
            idx = next((k for k, i in enumerate(items) if i.id == start_after), None)
            if idx is not None:
                items = items[idx + 1 :]
        page = items[:page_size]
        nxt = items[page_size].id if len(items) > page_size else None
        return Page(items=page, next_page_token=nxt)

    def get_by_student_and_date(self, student_id, date):
        for i in self.store.values():
            if i.student_id == student_id and i.date == date:
                return i
        return None

    def list_by_student_range(self, student_id, start_date=None, end_date=None, **kwargs):
        kwargs.setdefault("order_by", "date")
        kwargs.setdefault("desc", False)
        flt = [("student_id", "==", student_id)]
        if start_date:
            flt.append(("date", ">=", start_date))
        if end_date:
            flt.append(("date", "<=", end_date))
        return self.list(filters=flt, **kwargs)

    def list_all(self, **kwargs):
        return self.list(**kwargs)


class FakeStudentRepo:
    def __init__(self, students=None):
        self.store = {s.id: s for s in (students or [])}

    def get(self, doc_id):
        return self.store.get(doc_id)

    def list(self, *, filters=None, order_by=None, desc=False, page_size=20, start_after=None):
        items = list(self.store.values())
        for f in filters or []:
            field, op, val = f
            if op == "==":
                items = [i for i in items if getattr(i, field) == val]
            elif op == "array_contains":
                items = [i for i in items if val in getattr(i, field, [])]
        if order_by:
            items.sort(key=lambda i: getattr(i, order_by), reverse=desc)
        page = items[:page_size]
        nxt = items[page_size].id if len(items) > page_size else None
        return Page(items=page, next_page_token=nxt)

    def list_by_class(self, class_id, **kwargs):
        return self.list(filters=[("class_id", "==", class_id)], **kwargs)

    def list_by_name(self, name, **kwargs):
        return self.list(filters=[("name", "==", name)], **kwargs)


@pytest.fixture
def setup():
    att = FakeAttendanceRepo()
    stu = FakeStudentRepo(
        [
            StudentProfile(id="s1", user_id="s1", name="Rahul", class_id="c1"),
            StudentProfile(id="s2", user_id="s2", name="Rahul", class_id="c2"),
            StudentProfile(id="s3", user_id="s3", name="Priya", class_id="c1"),
        ]
    )
    svc.set_attendance_repository(att)
    svc.set_student_repository(stu)
    yield att, stu
    svc.set_attendance_repository(None)
    svc.set_student_repository(None)


def student_ctx(uid="s1"):
    return build_authorization_context(
        UserProfile(id=uid, firebase_uid=f"fb_{uid}", name="R", role=Role.STUDENT,
                    is_active=True, student_id=uid)
    )


def parent_ctx(uid="p1", child_ids=None):
    return build_authorization_context(
        UserProfile(id=uid, firebase_uid=f"fb_{uid}", name="P", role=Role.PARENT,
                    is_active=True, child_ids=child_ids or ["s1"])
    )


def teacher_ctx(uid="t1"):
    # A separate student repo scopes the teacher's authorized students to c1
    # (s1, s2, s5) without affecting the global name-resolution repo below.
    auth_students = FakeStudentRepo(
        [
            StudentProfile(id="s1", user_id="s1", name="Rahul", class_id="c1"),
            StudentProfile(id="s2", user_id="s2", name="Rahul", class_id="c1"),
            StudentProfile(id="s5", user_id="s5", name="Sam", class_id="c1"),
        ]
    )
    return build_authorization_context(
        UserProfile(id=uid, firebase_uid=f"fb_{uid}", name="T", role=Role.TEACHER,
                    is_active=True, teacher_class_ids=["c1"]),
        student_repo=auth_students,
    )


def principal_ctx(uid="pr1"):
    return build_authorization_context(
        UserProfile(id=uid, firebase_uid=f"fb_{uid}", name="PR", role=Role.PRINCIPAL,
                    is_active=True)
    )


# ---------------- Name resolution / ambiguity ----------------
def test_resolve_by_id():
    amb = svc.resolve_student_reference(student_id="s1")
    assert amb.resolved_id == "s1" and not amb.ambiguous


def test_resolve_single_name(setup):
    amb = svc.resolve_student_reference(name="Priya")
    assert amb.resolved_id == "s3" and not amb.ambiguous


def test_resolve_ambiguous_name(setup):
    amb = svc.resolve_student_reference(name="Rahul")
    assert amb.ambiguous is True
    assert {c.student_id for c in amb.candidates} == {"s1", "s2"}


def test_resolve_unknown_name(setup):
    amb = svc.resolve_student_reference(name="Nobody")
    assert amb.resolved_id is None and not amb.ambiguous


# ---------------- Student own attendance ----------------
def test_student_own_attendance_allowed(setup):
    recs = svc.get_student_attendance(student_ctx("s1"), "s1")
    assert isinstance(recs, list)


def test_student_cannot_view_other_student(setup):
    with pytest.raises(AppError) as exc:
        svc.get_student_attendance(student_ctx("s1"), "s3")
    assert exc.value.code == "FORBIDDEN"


# ---------------- Parent child attendance ----------------
def test_parent_child_attendance_allowed(setup):
    recs = svc.get_child_attendance(parent_ctx("p1", child_ids=["s1"]), "s1")
    assert isinstance(recs, list)


def test_parent_cannot_view_unrelated_child(setup):
    with pytest.raises(AppError) as exc:
        svc.get_child_attendance(parent_ctx("p1", child_ids=["s1"]), "s3")
    assert exc.value.code == "FORBIDDEN"


# ---------------- Teacher mark attendance ----------------
def test_teacher_mark_attendance(setup):
    rec = svc.mark_attendance(teacher_ctx("t1"), "s1", "2026-08-16", AttendanceStatus.PRESENT)
    assert rec.status == "PRESENT"
    assert rec.marked_by == "t1"
    # Upsert: marking again updates the same record.
    rec2 = svc.mark_attendance(teacher_ctx("t1"), "s1", "2026-08-16", AttendanceStatus.LATE)
    assert rec2.status == "LATE"
    assert rec2.id == rec.id


def test_teacher_cannot_mark_unauthorized_student(setup):
    with pytest.raises(AppError) as exc:
        svc.mark_attendance(teacher_ctx("t1"), "s3", "2026-08-16", AttendanceStatus.PRESENT)
    assert exc.value.code == "FORBIDDEN"


def test_teacher_mark_missing_student(setup):
    with pytest.raises(AppError) as exc:
        svc.mark_attendance(teacher_ctx("t1"), "s5", "2026-08-16", AttendanceStatus.PRESENT)
    assert exc.value.code == "NOT_FOUND"


# ---------------- Principal analytics ----------------
def test_principal_overall_attendance(setup):
    att, _ = setup
    for sid, st in [("s1", "PRESENT"), ("s1", "ABSENT"), ("s3", "LATE")]:
        att.create(AttendanceRecord(id="", student_id=sid, class_id="c1",
                                     date="2026-08-16", status=st, marked_by="t1"))
    summary = svc.get_overall_attendance(principal_ctx("pr1"))
    assert summary.total == 3
    assert summary.present == 1 and summary.absent == 1 and summary.late == 1
    assert summary.attendance_rate == pytest.approx(33.33, abs=0.01)


def test_non_principal_cannot_view_analytics(setup):
    with pytest.raises(AppError) as exc:
        svc.get_overall_attendance(student_ctx("s1"))
    assert exc.value.code == "FORBIDDEN"


# ---------------- Missing date handling ----------------
def test_mark_attendance_requires_date(setup):
    with pytest.raises(ValidationError):
        # Missing required `date` field.
        from app.schemas.attendance import MarkAttendanceInput

        MarkAttendanceInput(student_id="s1", status=AttendanceStatus.PRESENT)
