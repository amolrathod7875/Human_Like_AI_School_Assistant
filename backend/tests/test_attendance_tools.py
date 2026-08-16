import asyncio
import pytest

from app.ai.tools import (
    InvalidArgumentsError,
    ToolAuthorizationError,
    execute_tool,
    get_tool,
    list_tool_definitions,
    list_tools,
    register_tool,
    reset_registry,
    set_authorization_hook,
)
from app.ai.tools.attendance_tools import (
    GetChildAttendanceTool,
    GetOverallAttendanceTool,
    GetOwnAttendanceTool,
    MarkAttendanceTool,
)
from app.ai.tools.errors import ToolNotFoundError
from app.auth.authorization.context import build_authorization_context
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
    reset_registry()
    register_tool(GetOwnAttendanceTool())
    register_tool(GetChildAttendanceTool())
    register_tool(GetOverallAttendanceTool())
    register_tool(MarkAttendanceTool())
    yield att, stu
    svc.set_attendance_repository(None)
    svc.set_student_repository(None)
    reset_registry()


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


def test_tools_registered(setup):
    names = {t.name for t in list_tools()}
    assert names == {
        "get_own_attendance",
        "get_child_attendance",
        "get_overall_attendance",
        "mark_attendance",
    }
    assert len(list_tool_definitions()) == 4


def test_unknown_tool_rejected(setup):
    with pytest.raises(ToolNotFoundError):
        asyncio.run(execute_tool("nope", student_ctx("s1"), {}))


def test_student_own_attendance_tool(setup):
    result = asyncio.run(execute_tool("get_own_attendance", student_ctx("s1"), {}))
    assert isinstance(result, list)


def test_student_cannot_use_child_tool(setup):
    with pytest.raises(ToolAuthorizationError):
        asyncio.run(
            execute_tool("get_child_attendance", student_ctx("s1"),
                         {"student_id": "s1"})
        )


def test_teacher_mark_via_tool(setup):
    result = asyncio.run(
        execute_tool("mark_attendance", teacher_ctx("t1"),
                     {"student_id": "s1", "date": "2026-08-16",
                      "status": "PRESENT"})
    )
    assert result.status == "PRESENT"


def test_teacher_mark_unauthorized_via_tool(setup):
    with pytest.raises(ToolAuthorizationError):
        asyncio.run(
            execute_tool("mark_attendance", teacher_ctx("t1"),
                         {"student_id": "s3", "date": "2026-08-16",
                          "status": "PRESENT"})
        )


def test_principal_overall_via_tool(setup):
    result = asyncio.run(execute_tool("get_overall_attendance", principal_ctx("pr1"), {}))
    assert result.total == 0


def test_ambiguous_name_rejected_by_tool(setup):
    with pytest.raises(InvalidArgumentsError):
        asyncio.run(
            execute_tool("mark_attendance", teacher_ctx("t1"),
                         {"name": "Rahul", "date": "2026-08-16",
                          "status": "PRESENT"})
        )


def test_unknown_name_rejected_by_tool(setup):
    with pytest.raises(InvalidArgumentsError):
        asyncio.run(
            execute_tool("mark_attendance", teacher_ctx("t1"),
                         {"name": "Nobody", "date": "2026-08-16",
                          "status": "PRESENT"})
        )
