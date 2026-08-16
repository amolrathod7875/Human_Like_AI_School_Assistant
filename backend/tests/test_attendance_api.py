import pytest
from fastapi.testclient import TestClient

from app.auth.authorization.context import build_authorization_context
from app.main import create_app
from app.repositories.base import Page
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
def client():
    att = FakeAttendanceRepo()
    stu = FakeStudentRepo(
        [
            StudentProfile(id="s1", user_id="s1", name="Rahul", class_id="c1"),
            StudentProfile(id="s3", user_id="s3", name="Priya", class_id="c1"),
        ]
    )
    svc.set_attendance_repository(att)
    svc.set_student_repository(stu)

    app = create_app()

    def make_ctx(role, uid, **kw):
        student_repo = None
        if role == Role.TEACHER:
            student_repo = FakeStudentRepo(
                [
                    StudentProfile(id="s1", user_id="s1", name="Rahul", class_id="c1"),
                    StudentProfile(id="s2", user_id="s2", name="Rahul", class_id="c1"),
                ]
            )
        return build_authorization_context(
            UserProfile(id=uid, firebase_uid=f"fb_{uid}", name="X", role=role,
                        is_active=True, **kw),
            student_repo=student_repo,
        )

    overrides = {
        "STUDENT": make_ctx(Role.STUDENT, "s1", student_id="s1"),
        "PARENT": make_ctx(Role.PARENT, "p1", child_ids=["s1"]),
        "TEACHER": make_ctx(Role.TEACHER, "t1", teacher_class_ids=["c1"]),
        "PRINCIPAL": make_ctx(Role.PRINCIPAL, "pr1"),
    }

    def ctx_for(role):
        async def _dep():
            return overrides[role]
        return _dep

    # Override the exact dependency object referenced by the router.
    from app.api.v1 import attendance as att_module

    app.dependency_overrides[att_module.get_auth_context] = ctx_for("STUDENT")

    yield TestClient(app), app, ctx_for

    svc.set_attendance_repository(None)
    svc.set_student_repository(None)
    app.dependency_overrides.clear()


def set_role(client, app, ctx_for, role):
    from app.api.v1 import attendance as att_module

    app.dependency_overrides[att_module.get_auth_context] = ctx_for(role)


def test_student_views_own_attendance(client):
    c, app, ctx_for = client
    set_role(c, app, ctx_for, "STUDENT")
    r = c.get("/api/v1/attendance/student/s1")
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_student_cannot_view_other_student(client):
    c, app, ctx_for = client
    set_role(c, app, ctx_for, "STUDENT")
    r = c.get("/api/v1/attendance/student/s3")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_teacher_marks_attendance(client):
    c, app, ctx_for = client
    set_role(c, app, ctx_for, "TEACHER")
    r = c.post(
        "/api/v1/attendance",
        json={"student_id": "s1", "date": "2026-08-16", "status": "PRESENT"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "PRESENT"


def test_student_cannot_mark_attendance(client):
    c, app, ctx_for = client
    set_role(c, app, ctx_for, "STUDENT")
    r = c.post(
        "/api/v1/attendance",
        json={"student_id": "s1", "date": "2026-08-16", "status": "PRESENT"},
    )
    assert r.status_code == 403


def test_principal_overall_analytics(client):
    c, app, ctx_for = client
    set_role(c, app, ctx_for, "PRINCIPAL")
    r = c.get("/api/v1/attendance/analytics/overall")
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 0


def test_non_principal_cannot_view_analytics(client):
    c, app, ctx_for = client
    set_role(c, app, ctx_for, "STUDENT")
    r = c.get("/api/v1/attendance/analytics/overall")
    assert r.status_code == 403


def test_mark_attendance_missing_date(client):
    c, app, ctx_for = client
    set_role(c, app, ctx_for, "TEACHER")
    r = c.post(
        "/api/v1/attendance",
        json={"student_id": "s1", "status": "PRESENT"},
    )
    assert r.status_code == 422
