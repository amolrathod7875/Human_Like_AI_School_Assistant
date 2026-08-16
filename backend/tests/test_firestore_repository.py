import pytest
from datetime import datetime, timezone
from google.cloud import exceptions as gexc

from firebase_admin import firestore as _fs

# Mimic Firestore's server-side substitution of SERVER_TIMESTAMP on write.
_SERVER_TIMESTAMP = _fs.SERVER_TIMESTAMP
_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _clean(data):
    return {k: (_NOW if v is _SERVER_TIMESTAMP else v) for k, v in data.items()}

from app.repositories.base import RepositoryError, map_firestore_error
from app.repositories.firestore.attendance import AttendanceRepository
from app.repositories.firestore.audit_log import AuditLogRepository
from app.repositories.firestore.class_ import ClassRepository
from app.repositories.firestore.conversation import ConversationRepository
from app.repositories.firestore.student import StudentRepository
from app.repositories.firestore.support_request import SupportRequestRepository
from app.repositories.firestore.user import UserRepository
from app.schemas.collections import (
    AttendanceRecord,
    AuditLog,
    ClassProfile,
    Conversation,
    StudentProfile,
    SupportRequest,
)
from app.schemas.user import UserProfile


# ----- In-memory fake Firestore client (subset used by the base repo) -----
class FakeSnapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return self._data


class FakeDocument:
    def __init__(self, collection, doc_id):
        self._collection = collection
        self.id = doc_id

    def get(self):
        return FakeSnapshot(self.id, self._collection._docs.get(self.id))

    def set(self, data):
        self._collection._docs[self.id] = _clean(dict(data))

    def update(self, data):
        if self.id not in self._collection._docs:
            raise gexc.NotFound(f"missing {self.id}")
        self._collection._docs[self.id].update(_clean(data))

    def delete(self):
        self._collection._docs.pop(self.id, None)


class FakeQuery:
    def __init__(
        self, collection, filters=None, order_by=None, start_after=None, limit=None
    ):
        self._collection = collection
        self._filters = filters or []
        self._order_by = order_by
        self._start_after = start_after
        self._limit = limit

    def where(self, f, op, v):
        return FakeQuery(
            self._collection, self._filters + [(f, op, v)],
            self._order_by, self._start_after, self._limit,
        )

    def order_by(self, f):
        return FakeQuery(
            self._collection, self._filters, f, self._start_after, self._limit
        )

    def start_after(self, token):
        return FakeQuery(
            self._collection, self._filters, self._order_by, token, self._limit
        )

    def limit(self, n):
        return FakeQuery(
            self._collection, self._filters, self._order_by, self._start_after, n
        )

    def get(self):
        docs = []
        for doc_id, data in self._collection._docs.items():
            ok = True
            for field, op, value in self._filters:
                cur = data.get(field)
                if op == "==":
                    ok = cur == value
                elif op == "array_contains":
                    ok = value in (cur or [])
                else:
                    ok = False
                if not ok:
                    break
            if ok:
                docs.append(FakeSnapshot(doc_id, data))
        if self._order_by:
            field = self._order_by.lstrip("-")
            reverse = self._order_by.startswith("-")
            docs.sort(key=lambda d: d.to_dict().get(field) or "", reverse=reverse)
        if self._start_after:
            idx = next(
                (i for i, d in enumerate(docs) if d.id == self._start_after), None
            )
            if idx is not None:
                docs = docs[idx + 1 :]
        if self._limit is not None:
            docs = docs[: self._limit]
        return docs


class FakeCollection:
    def __init__(self, client, name):
        self._client = client
        self.name = name
        self._docs = client._store.setdefault(name, {})

    def document(self, doc_id=None):
        if doc_id is None:
            doc_id = f"auto_{len(self._docs) + 1}"
        return FakeDocument(self, doc_id)

    def where(self, f, op, v):
        return FakeQuery(self, [(f, op, v)])

    def limit(self, n):
        return FakeQuery(self, limit=n)

    def order_by(self, f):
        return FakeQuery(self, order_by=f)


class FakeFirestoreClient:
    def __init__(self):
        self._store = {}

    def collection(self, name):
        return FakeCollection(self, name)


def client():
    return FakeFirestoreClient()


# ----- Tests -----
def test_get_returns_model_and_missing_returns_none():
    repo = UserRepository(client=client())
    repo.create(
        UserProfile(id="u1", firebase_uid="fb1", name="Amit", role="PARENT"),
        doc_id="u1",
    )
    got = repo.get("u1")
    assert got is not None and got.id == "u1"
    assert got.role.value == "PARENT"
    assert repo.get("nope") is None


def test_create_with_auto_id():
    repo = UserRepository(client=client())
    created = repo.create(
        UserProfile(id="ignored", firebase_uid="fb", name="B")
    )
    assert created.id  # Firestore-assigned id
    assert repo.get(created.id) is not None


def test_update_applies_changes_and_missing_raises():
    repo = UserRepository(client=client())
    repo.create(
        UserProfile(id="u1", firebase_uid="fb", name="Old"), doc_id="u1"
    )
    repo.update("u1", {"name": "New"})
    assert repo.get("u1").name == "New"

    with pytest.raises(RepositoryError) as exc:
        repo.update("missing", {"name": "x"})
    assert exc.value.code == "NOT_FOUND"


def test_delete():
    repo = UserRepository(client=client())
    repo.create(
        UserProfile(id="u1", firebase_uid="fb", name="D"), doc_id="u1"
    )
    repo.delete("u1")
    assert repo.get("u1") is None


def test_user_repo_by_firebase_uid():
    repo = UserRepository(client=client())
    repo.create(
        UserProfile(id="u1", firebase_uid="fb1", name="A", role="TEACHER"),
        doc_id="u1",
    )
    found = repo.get_by_firebase_uid("fb1")
    assert found is not None and found.id == "u1"
    assert repo.get_by_firebase_uid("absent") is None


def test_list_filter_and_pagination():
    repo = UserRepository(client=client())
    for i in range(5):
        repo.create(
            UserProfile(
                id=f"u{i}", firebase_uid=f"fb{i}", name=f"U{i}", role="STUDENT"
            ),
            doc_id=f"u{i}",
        )
    page = repo.list(filters=[("role", "==", "STUDENT")], page_size=2)
    assert len(page.items) == 2
    assert page.next_page_token is not None

    page2 = repo.list(
        filters=[("role", "==", "STUDENT")],
        page_size=2,
        start_after=page.next_page_token,
    )
    assert len(page2.items) == 2

    page3 = repo.list(
        filters=[("role", "==", "STUDENT")],
        page_size=2,
        start_after=page2.next_page_token,
    )
    assert len(page3.items) == 1
    assert page3.next_page_token is None


def test_student_class_and_parent_queries():
    repo = StudentRepository(client=client())
    repo.create(
        StudentProfile(
            id="s1", user_id="u1", name="St", class_id="c1", parent_ids=["p1"]
        ),
        doc_id="s1",
    )
    assert repo.list_by_class("c1").items[0].id == "s1"
    assert repo.list_by_parent("p1").items[0].id == "s1"


def test_class_teacher_query():
    repo = ClassRepository(client=client())
    repo.create(
        ClassProfile(id="c1", name="5A", teacher_id="t1"), doc_id="c1"
    )
    assert repo.list_by_teacher("t1").items[0].id == "c1"


def test_attendance_queries():
    repo = AttendanceRepository(client=client())
    repo.create(
        AttendanceRecord(
            id="a1", student_id="s1", class_id="c1", date="2026-08-16", status="PRESENT"
        ),
        doc_id="a1",
    )
    assert repo.list_by_student("s1").items[0].status == "PRESENT"
    assert repo.list_by_class("c1").items[0].id == "a1"


def test_conversation_and_support_request_queries():
    convo = ConversationRepository(client=client())
    convo.create(Conversation(id="cv1", user_id="u1", title="Hi"), doc_id="cv1")
    assert convo.list_by_user("u1").items[0].id == "cv1"

    sr = SupportRequestRepository(client=client())
    sr.create(
        SupportRequest(id="r1", user_id="u1", subject="S", message="M", status="OPEN"),
        doc_id="r1",
    )
    assert sr.list_by_user("u1").items[0].id == "r1"
    assert sr.list_by_status("OPEN").items[0].id == "r1"


def test_audit_log_record():
    repo = AuditLogRepository(client=client())
    log = repo.record("u1", "LOGIN", target="session", metadata={"ip": "x"})
    assert log.id
    stored = repo.get(log.id)
    assert stored is not None and stored.action == "LOGIN"


def test_error_mapping():
    assert map_firestore_error(gexc.NotFound("x")).code == "NOT_FOUND"
    assert map_firestore_error(gexc.Conflict("x")).code == "ALREADY_EXISTS"
    assert map_firestore_error(gexc.Forbidden("x")).code == "PERMISSION_DENIED"
    assert map_firestore_error(gexc.BadRequest("x")).code == "INVALID_ARGUMENT"
    assert map_firestore_error(RuntimeError("x")).code == "REPOSITORY_ERROR"
