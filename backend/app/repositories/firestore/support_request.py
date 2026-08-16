from typing import Optional

from app.repositories.base import FirestoreRepository, Page
from app.schemas.collections import SupportRequest


class SupportRequestRepository(FirestoreRepository[SupportRequest]):
    def __init__(self, client=None) -> None:
        super().__init__(SupportRequest, "support_requests", client=client)

    def list_by_user(
        self, user_id: str, **kwargs
    ) -> Page[SupportRequest]:
        return self.list(filters=[("user_id", "==", user_id)], **kwargs)

    def list_by_status(
        self, status: str, **kwargs
    ) -> Page[SupportRequest]:
        return self.list(filters=[("status", "==", status)], **kwargs)
