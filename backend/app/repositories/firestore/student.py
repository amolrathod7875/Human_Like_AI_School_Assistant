from typing import Optional

from app.repositories.base import FirestoreRepository, Page
from app.schemas.collections import StudentProfile


class StudentRepository(FirestoreRepository[StudentProfile]):
    def __init__(self, client=None) -> None:
        super().__init__(StudentProfile, "students", client=client)

    def list_by_class(
        self, class_id: str, **kwargs
    ) -> Page[StudentProfile]:
        return self.list(filters=[("class_id", "==", class_id)], **kwargs)

    def list_by_parent(
        self, parent_id: str, **kwargs
    ) -> Page[StudentProfile]:
        return self.list(
            filters=[("parent_ids", "array_contains", parent_id)], **kwargs
        )
