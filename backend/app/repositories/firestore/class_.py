from typing import Optional

from app.repositories.base import FirestoreRepository, Page
from app.schemas.collections import ClassProfile


class ClassRepository(FirestoreRepository[ClassProfile]):
    def __init__(self, client=None) -> None:
        super().__init__(ClassProfile, "classes", client=client)

    def list_by_teacher(
        self, teacher_id: str, **kwargs
    ) -> Page[ClassProfile]:
        return self.list(filters=[("teacher_id", "==", teacher_id)], **kwargs)
