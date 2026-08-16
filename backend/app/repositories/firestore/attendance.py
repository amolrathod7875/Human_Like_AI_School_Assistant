from typing import Optional

from app.repositories.base import FirestoreRepository, Page
from app.schemas.collections import AttendanceRecord


class AttendanceRepository(FirestoreRepository[AttendanceRecord]):
    def __init__(self, client=None) -> None:
        super().__init__(AttendanceRecord, "attendance", client=client)

    def list_by_student(
        self, student_id: str, **kwargs
    ) -> Page[AttendanceRecord]:
        return self.list(filters=[("student_id", "==", student_id)], **kwargs)

    def list_by_class(
        self, class_id: str, **kwargs
    ) -> Page[AttendanceRecord]:
        return self.list(filters=[("class_id", "==", class_id)], **kwargs)
