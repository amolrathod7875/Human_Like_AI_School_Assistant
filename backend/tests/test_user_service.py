import pytest

from app.repositories.user_repository import set_user_repository
from app.schemas.user import Role, UserProfile
from app.services import user_service


class FakeUserRepository:
    def __init__(self, by_id=None, by_uid=None):
        self._by_id = by_id or {}
        self._by_uid = by_uid or {}

    def get_by_id(self, user_id):
        return self._by_id.get(user_id)

    def get_by_firebase_uid(self, firebase_uid):
        return self._by_uid.get(firebase_uid)


@pytest.fixture
def repo():
    r = FakeUserRepository()
    set_user_repository(r)
    yield r
    set_user_repository(None)


def _profile(user_id, role, **kwargs):
    return UserProfile(
        id=user_id, firebase_uid=f"fb_{user_id}", name="Name", role=role, **kwargs
    )


def test_each_role_loads_correctly(repo):
    repo._by_id = {
        "s1": _profile("s1", Role.STUDENT),
        "p1": _profile("p1", Role.PARENT),
        "t1": _profile("t1", Role.TEACHER),
        "pr1": _profile("pr1", Role.PRINCIPAL),
    }
    assert user_service.get_user_role("s1") == Role.STUDENT
    assert user_service.get_user_role("p1") == Role.PARENT
    assert user_service.get_user_role("t1") == Role.TEACHER
    assert user_service.get_user_role("pr1") == Role.PRINCIPAL


def test_parent_child_relationship_resolves(repo):
    child = _profile("c1", Role.STUDENT, student_id="c1", parent_ids=["p1"])
    parent = _profile("p1", Role.PARENT, child_ids=["c1"])
    repo._by_id = {"c1": child, "p1": parent}

    children = user_service.get_children_for_parent("p1")
    assert [c.id for c in children] == ["c1"]
    assert children[0].role == Role.STUDENT


def test_teacher_class_relationship_resolves(repo):
    teacher = _profile("t1", Role.TEACHER, teacher_class_ids=["class_a", "class_b"])
    repo._by_id = {"t1": teacher}
    assert user_service.get_teacher_classes("t1") == ["class_a", "class_b"]


def test_inactive_user_is_rejected(repo):
    inactive = _profile("x1", Role.STUDENT, is_active=False)
    repo._by_id = {"x1": inactive}

    assert user_service.is_active_user("x1") is False
    # Profile is still returned; the caller must reject inactive users.
    assert user_service.get_user_by_id("x1").is_active is False
    # Unknown users are also not active.
    assert user_service.is_active_user("missing") is False


def test_fake_role_value_does_not_override_stored_role(repo):
    # The stored role is PARENT. A caller claiming STUDENT (frontend/LLM/param)
    # has no effect: the role is read only from the store.
    repo._by_id = {"p1": _profile("p1", Role.PARENT)}
    assert user_service.get_user_role("p1") == Role.PARENT


def test_get_user_by_firebase_uid(repo):
    profile = _profile("u1", Role.TEACHER)
    repo._by_uid = {"fb_u1": profile}
    loaded = user_service.get_user_by_firebase_uid("fb_u1")
    assert loaded is not None and loaded.id == "u1"
