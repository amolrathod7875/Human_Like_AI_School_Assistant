from app.repositories.base import FirestoreRepository
from app.schemas.user import UserProfile


class UserRepository(FirestoreRepository[UserProfile]):
    """Firestore repository for the `users` collection.

    This is the shared implementation backing Section 03's `UserRepository`
    protocol (service-facing). It adds the two lookup methods the service needs.
    """

    def __init__(self, client=None) -> None:
        super().__init__(UserProfile, "users", client=client)

    def get_by_id(self, user_id: str):
        return self.get(user_id)

    def get_by_firebase_uid(self, firebase_uid: str):
        page = self.list(
            filters=[("firebase_uid", "==", firebase_uid)], page_size=1
        )
        return page.items[0] if page.items else None
