from typing import Optional

from app.repositories.base import FirestoreRepository, Page
from app.schemas.collections import Conversation


class ConversationRepository(FirestoreRepository[Conversation]):
    def __init__(self, client=None) -> None:
        super().__init__(Conversation, "conversations", client=client)

    def list_by_user(
        self, user_id: str, **kwargs
    ) -> Page[Conversation]:
        return self.list(filters=[("user_id", "==", user_id)], **kwargs)
