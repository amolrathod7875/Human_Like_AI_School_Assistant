from typing import Any, Optional

from app.repositories.base import FirestoreRepository
from app.schemas.collections import Message


class MessageRepository(FirestoreRepository[Message]):
    """Repository for the `conversations/{conversation_id}/messages` subcollection.

    Only the collection reference differs from the generic base; all CRUD,
    mapping, timestamps, pagination, and error mapping are inherited.
    """

    def __init__(self, conversation_id: str, client: Any = None) -> None:
        super().__init__(Message, "messages", client=client)
        self.conversation_id = conversation_id

    @property
    def _coll(self):
        return (
            self.client.collection("conversations")
            .document(self.conversation_id)
            .collection("messages")
        )
