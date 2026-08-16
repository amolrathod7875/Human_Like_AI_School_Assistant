from typing import List, Optional, Protocol, runtime_checkable

from app.providers.firebase_provider import get_firebase_app
from app.schemas.user import Role, UserProfile

COLLECTION_NAME = "users"


@runtime_checkable
class UserRepository(Protocol):
    """Adapter interface for user-profile persistence.

    Keeps Firestore behind an interface so the service layer (and tests)
    depend on this contract, not on firebase-admin directly.
    """

    def get_by_firebase_uid(self, firebase_uid: str) -> Optional[UserProfile]:
        ...

    def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        ...


class FirestoreUserRepository:
    """Firestore-backed implementation reading the `users` collection."""

    def _collection(self):
        from firebase_admin import firestore

        app = get_firebase_app()
        return firestore.client(app=app).collection(COLLECTION_NAME)

    def get_by_firebase_uid(self, firebase_uid: str) -> Optional[UserProfile]:
        docs = (
            self._collection()
            .where("firebase_uid", "==", firebase_uid)
            .limit(1)
            .get()
        )
        for doc in docs:
            if doc.exists:
                return _to_profile(doc)
        return None

    def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        doc = self._collection().document(user_id).get()
        if not doc.exists:
            return None
        return _to_profile(doc)


def _to_profile(doc) -> UserProfile:
    data = dict(doc.to_dict() or {})
    data["id"] = doc.id

    raw_role = data.get("role")
    try:
        data["role"] = Role(raw_role) if raw_role else Role.STUDENT
    except ValueError:
        # Unknown role values fall back to STUDENT rather than failing the call.
        data["role"] = Role.STUDENT

    for field in ("child_ids", "parent_ids", "teacher_class_ids"):
        data.setdefault(field, [])

    return UserProfile(**data)


# Module-level repository holder. Tests inject a fake via set_user_repository().
_repo: Optional[UserRepository] = None


def set_user_repository(repo: Optional[UserRepository]) -> None:
    global _repo
    _repo = repo


def get_user_repository() -> UserRepository:
    global _repo
    if _repo is None:
        _repo = FirestoreUserRepository()
    return _repo
