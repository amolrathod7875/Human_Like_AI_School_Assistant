import asyncio
import pytest

from app.ai.tools import reset_registry, register_tool, execute_tool
from app.ai.tools.escalation_tools import (
    CreateManagementContactTool,
    CreateTeacherContactTool,
)
from app.ai.tools.errors import InvalidArgumentsError, ToolAuthorizationError
from app.auth.authorization.context import (
    AuthorizationContext,
    build_authorization_context,
)
from app.services import escalation_service as svc
from app.schemas.user import Role, UserProfile


def run_svc(coro):
    return asyncio.run(coro)


def run_tool(name, context, args):
    return asyncio.run(execute_tool(name, context, args))


# --------------------------------------------------------------- fakes / di
class FakeSupportRepo:
    def __init__(self):
        self.store = {}

    def create(self, model):
        self.store[model.id] = model
        return model

    def get(self, doc_id):
        return self.store.get(doc_id)

    def update(self, doc_id, changes):
        self.store[doc_id] = self.store[doc_id].model_copy(update=changes)
        return self.store[doc_id]

    def list(self, *, filters=None, order_by=None, desc=False, page_size=20,
             start_after=None):
        from app.repositories.base import Page

        items = list(self.store.values())
        return Page(items=items[:page_size])


@pytest.fixture
def escalation_env():
    repo = FakeSupportRepo()
    svc.set_support_repository(repo)
    svc.set_human_support_adapter(svc.MockHumanSupportAdapter(outcome="CONFIRMED"))
    yield repo
    svc.set_support_repository(None)
    svc.set_human_support_adapter(None)


class FakeUserRepo:
    def __init__(self, students=None):
        self.store = {s.id: s for s in (students or [])}

    def get(self, doc_id):
        return self.store.get(doc_id)

    def list(self, *, filters=None, order_by=None, desc=False, page_size=20,
             start_after=None):
        from app.repositories.base import Page

        return Page(items=list(self.store.values())[:page_size])

    def list_by_class(self, class_id, **kwargs):
        return self.list(filters=[("class_id", "==", class_id)], **kwargs)

    def list_by_name(self, name, **kwargs):
        return self.list(filters=[("name", "==", name)], **kwargs)


class FakeStudentRepo:
    def __init__(self, students=None):
        self.store = {s.id: s for s in (students or [])}
    def get(self, doc_id):
        return self.store.get(doc_id)
    def list(self, *, filters=None, order_by=None, desc=False, page_size=20,
             start_after=None):
        from app.repositories.base import Page
        return Page(items=list(self.store.values())[:page_size])
    def list_by_class(self, class_id, **kwargs):
        return self.list(filters=[("class_id", "==", class_id)], **kwargs)
    def list_by_name(self, name, **kwargs):
        return self.list(filters=[("name", "==", name)], **kwargs)


def ctx(role, uid, **kw):
    rel = AuthorizationContext.model_validate({
        'user_id': uid,
        'firebase_uid': 'fb_' + uid,
        'role': role,
        'active': True,
        'relationship': {
            'student_id': kw.get('student_id'),
            'child_ids': kw.get('child_ids', []),
            'class_ids': kw.get('teacher_class_ids', []),
            'authorized_student_ids': kw.get('teacher_class_ids', []),
            'school_wide': role == Role.PRINCIPAL,
        },
    })
    return rel


def test_parent_teacher_escalation_confirmed(escalation_env):
    request = run_svc(
        svc.request_teacher_contact(
            ctx(Role.PARENT, "p1", child_ids=["s1"]), "s1", "Attendance concern"
        )
    )
    assert request.status == "CONFIRMED"
    assert request.target_type == "TEACHER"
    assert request.requester_role == "PARENT"
    assert request.student_id == "s1"


def test_teacher_management_escalation_confirmed(escalation_env):
    request = run_svc(
        svc.request_management_contact(
            ctx(Role.TEACHER, "t1", teacher_class_ids=["c1"]), "Schedule concern"
        )
    )
    assert request.status == "CONFIRMED"
    assert request.target_type == "MANAGEMENT"


def test_parent_management_escalation_denied(escalation_env):
    from app.core.errors import AppError

    with pytest.raises(AppError):
        run_svc(
            svc.request_management_contact(
                ctx(Role.PARENT, "p1", child_ids=["s1"]), " Anything"
            )
        )


def test_student_teacher_escalation_denied(escalation_env):
    from app.core.errors import AppError

    with pytest.raises(AppError):
        run_svc(
            svc.request_teacher_contact(
                ctx(Role.STUDENT, "s1", student_id="s1"), "s1", " Anything"
            )
        )


# --------------------------------------------------- mock failure handling
def test_mock_failure_is_persisted_as_failed(escalation_env):
    svc.set_human_support_adapter(svc.MockHumanSupportAdapter(outcome="FAILED"))
    request = run_svc(
        svc.request_teacher_contact(
            ctx(Role.PARENT, "p1", child_ids=["s1"]), "s1", "Attendance concern"
        )
    )
    assert request.status == "FAILED"


def test_adapter_exception_is_handled_as_failed(escalation_env):
    def boom(req):
        raise RuntimeError("down")

    svc.set_human_support_adapter(svc.MockHumanSupportAdapter(outcome=boom))
    request = run_svc(
        svc.request_teacher_contact(
            ctx(Role.PARENT, "p1", child_ids=["s1"]), "s1", "Attendance concern"
        )
    )
    assert request.status == "FAILED"


# ----------------------------------------------------- request status retrieval
def test_get_request_owner_can_read(escalation_env):
    created = run_svc(
        svc.request_teacher_contact(
            ctx(Role.PARENT, "p1", child_ids=["s1"]), "s1", "Attendance concern"
        )
    )
    fetched = run_svc(svc.get_request(created.id, ctx(Role.PARENT, "p1", child_ids=["s1"])))
    assert fetched.id == created.id


def test_get_request_non_owner_denied(escalation_env):
    from app.core.errors import AppError

    created = run_svc(
        svc.request_teacher_contact(
            ctx(Role.PARENT, "p1", child_ids=["s1"]), "s1", "Attendance concern"
        )
    )
    with pytest.raises(AppError) as exc:
        run_svc(svc.get_request(created.id, ctx(Role.PARENT, "p2", child_ids=["s9"])))
    assert exc.value.code == "FORBIDDEN"


def test_get_request_not_found(escalation_env):
    from app.core.errors import AppError

    with pytest.raises(AppError) as exc:
        run_svc(svc.get_request("missing", ctx(Role.PARENT, "p1", child_ids=["s1"])))
    assert exc.value.code == "NOT_FOUND"


# --------------------------------------------------------------- tool behavior
def test_teacher_contact_tool_requires_confirmation(escalation_env):
    reset_registry()
    register_tool(CreateTeacherContactTool())
    with pytest.raises(InvalidArgumentsError):
        run_tool(
            "create_teacher_contact_request",
            ctx(Role.PARENT, "p1", child_ids=["s1"]),
            {"student_id": "s1", "reason": "Attendance", "confirmed": False},
        )


def test_teacher_contact_tool_executes_when_confirmed(escalation_env):
    reset_registry()
    register_tool(CreateTeacherContactTool())
    result = run_tool(
        "create_teacher_contact_request",
        ctx(Role.PARENT, "p1", child_ids=["s1"]),
        {"student_id": "s1", "reason": "Attendance", "confirmed": True},
    )
    assert result["status"] == "CONFIRMED"
    assert "confirmed" in result["message"].lower()


def test_management_contact_tool_unauthorized_role(escalation_env):
    reset_registry()
    register_tool(CreateManagementContactTool())
    with pytest.raises(ToolAuthorizationError):
        run_tool(
            "create_management_contact_request",
            ctx(Role.PARENT, "p1", child_ids=["s1"]),
            {"reason": "Anything", "confirmed": True},
        )


def test_management_contact_tool_teacher_confirmed(escalation_env):
    reset_registry()
    register_tool(CreateManagementContactTool())
    result = run_tool(
        "create_management_contact_request",
        ctx(Role.TEACHER, "t1", teacher_class_ids=["c1"]),
        {"reason": "Schedule", "confirmed": True},
    )
    assert result["status"] == "CONFIRMED"
