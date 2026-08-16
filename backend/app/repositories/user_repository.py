from typing import Optional, Protocol, runtime_checkable

from app.repositories.firestore.user import UserRepository as FirestoreUserRepository
from app.schemas.user import UserProfile

# Service-facing contract (Section 03). The concrete implementation is the
# generic Firestore UserRepository; its public methods match this protocol,
# so the Section 03 service layer is untouched.
@runtime_checkable
class UserRepository(Protocol):
    def get_by_firebase_uid(self, firebase_uid: str) -> Optional[UserProfile]:
        ...

    def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        ...


# Module-level repository holder. Tests inject a fake via set_user_repository().
_repo = None


def set_user_repository(repo: Optional[UserRepository]) -> None:
    global _repo
    _repo = repo


def get_user_repository() -> UserRepository:
    global _repo
    if _repo is None:
        _repo = FirestoreUserRepository()
    return _repo
