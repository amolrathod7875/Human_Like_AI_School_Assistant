import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.cohere.models import LLMResponse
from app.providers.cohere.provider import set_llm_provider
from app.schemas.user import Role
from app.services import escalation_service as svc
from app.services import conversation_service as conv_svc
from tests.test_escalation_service import FakeSupportRepo, FakeStudentRepo, FakeUserRepo
from tests.test_ai_orchestrator import ScriptedProvider, ctx, decision


@pytest.fixture
def api():
    conv_svc.set_conversation_repository(_ConvRepo())
    conv_svc.set_message_repository_factory(lambda cid: _MsgRepo())
    repo = FakeSupportRepo()
    svc.set_support_repository(repo)
    svc.set_human_support_adapter(svc.MockHumanSupportAdapter("CONFIRMED"))
    from app.repositories import user_repository
    user_repository.set_user_repository(FakeUserRepo())

    app = create_app()

    contexts = {
        "PARENT": ctx(Role.PARENT, "p1", child_ids=["s1"]),
        "STUDENT": ctx(Role.STUDENT, "s1", student_id="s1"),
        "TEACHER": ctx(Role.TEACHER, "t1", teacher_class_ids=["c1"]),
    }

    from app.api.v1 import escalation as esc_module

    def use(role):
        async def _dep():
            return contexts[role]

        app.dependency_overrides[esc_module.get_authorization_context] = _dep
        app.dependency_overrides[esc_module.get_authenticated_user] = (
            lambda: _user(contexts[role])
        )

    use("PARENT")

    with TestClient(app) as client:
        yield client, use, repo

    app.dependency_overrides.clear()
    set_llm_provider(None)
    conv_svc.set_conversation_repository(None)
    conv_svc.set_message_repository_factory(None)
    svc.set_support_repository(None)
    svc.set_human_support_adapter(None)


def _user(context):
    from app.auth.context import AuthenticatedUser

    return AuthenticatedUser(
        firebase_uid=context.firebase_uid, email=None, name=None
    )


class FakeUserRepo:
    def __init__(self, students=None):
        self.store = {s.id: s for s in (students or [])}
    def get(self, doc_id):
        return self.store.get(doc_id)
    def get_by_firebase_uid(self, firebase_uid):
        from app.schemas.user import Role, UserProfile
        uid = firebase_uid.replace("fb_", "")
        return UserProfile(id=uid, firebase_uid=firebase_uid, name="X",
                          role=Role.PARENT, is_active=True, child_ids=["s1"])
    def list(self, *, filters=None, order_by=None, desc=False, page_size=20,
             start_after=None):
        from app.repositories.base import Page
        return Page(items=list(self.store.values())[:page_size])
    def list_by_class(self, class_id, **kwargs):
        return self.list(filters=[("class_id", "==", class_id)], **kwargs)
    def list_by_name(self, name, **kwargs):
        return self.list(filters=[("name", "==", name)], **kwargs)

class _ConvRepo:
    def __init__(self):
        self.store = {}

    def create(self, model):
        cid = model.id or f"conv_{len(self.store) + 1}"
        created = model.model_copy(update={"id": cid})
        self.store[cid] = created
        return created

    def get(self, doc_id):
        return self.store.get(doc_id)


class _MsgRepo:
    def __init__(self):
        self.store = []

    def create(self, model):
        mid = model.id or f"msg_{len(self.store) + 1}"
        created = model.model_copy(update={"id": mid})
        self.store.append(created)
        return created

    def list(self, *, filters=None, order_by=None, desc=False, page_size=20,
             start_after=None):
        from app.repositories.base import Page

        items = list(self.store)
        if order_by == "timestamp":
            items.sort(key=lambda m: m.timestamp or 0, reverse=desc)
        return Page(items=items[:page_size])


def test_parent_teacher_escalation_api(api):
    client, use, repo = api
    response = client.post(
        "/api/v1/escalation/request",
        json={"target_type": "TEACHER", "student_id": "s1",
              "reason": "Attendance concern"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "CONFIRMED"
    assert data["target_type"] == "TEACHER"


def test_teacher_management_escalation_api(api):
    client, use, repo = api
    use("TEACHER")
    response = client.post(
        "/api/v1/escalation/request",
        json={"target_type": "MANAGEMENT", "reason": "Schedule concern"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "CONFIRMED"


def test_escalation_requires_student_for_teacher(api):
    client, use, repo = api
    response = client.post(
        "/api/v1/escalation/request",
        json={"target_type": "TEACHER", "reason": "x"},
    )
    assert response.status_code == 422


def test_student_cannot_escalate_api(api):
    client, use, repo = api
    use("STUDENT")
    response = client.post(
        "/api/v1/escalation/request",
        json={"target_type": "TEACHER", "student_id": "s1", "reason": "x"},
    )
    assert response.status_code == 403


def test_get_escalation_status_api(api):
    client, use, repo = api
    created = client.post(
        "/api/v1/escalation/request",
        json={"target_type": "TEACHER", "student_id": "s1",
              "reason": "Attendance concern"},
    ).json()["data"]
    rid = created["request_id"]

    fetched = client.get(f"/api/v1/escalation/{rid}")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["request_id"] == rid
    assert fetched.json()["data"]["status"] == "CONFIRMED"


def test_get_unknown_escalation_returns_404(api):
    client, use, repo = api
    response = client.get("/api/v1/escalation/does_not_exist")
    assert response.status_code == 404


def test_escalation_through_orchestrator(api):
    client, use, repo = api
    set_llm_provider(
        ScriptedProvider(
            [
                decision(
                    "REQUEST_TEACHER_CONTACT",
                    tool_calls=[{
                        "name": "create_teacher_contact_request",
                        "arguments": {"student_id": "s1",
                                      "reason": "Attendance concern",
                                      "confirmed": True},
                    }],
                ),
                LLMResponse(text="I've requested contact with the teacher.",
                            finish_reason="STOP"),
            ]
        )
    )
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Please contact my child's teacher about attendance."},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["tool_calls"][0]["status"] == "OK"
    # The request was actually persisted as CONFIRMED.
    assert any(r.status == "CONFIRMED" for r in repo.store.values())
