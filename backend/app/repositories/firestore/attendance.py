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

    def get_by_student_and_date(
        self, student_id: str, date: str
    ) -> Optional[AttendanceRecord]:
        page = self.list(
            filters=[("student_id", "==", student_id), ("date", "==", date)],
            page_size=1,
        )
        return page.items[0] if page.items else None

    def list_by_student_range(
        self,
        student_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Page[AttendanceRecord]:
        filters = [("student_id", "==", student_id)]
        if start_date is not None:
            filters.append(("date", ">=", start_date))
        if end_date is not None:
            filters.append(("date", "<=", end_date))
        kwargs.setdefault("order_by", "date")
        kwargs.setdefault("desc", False)
        return self.list(filters=filters, **kwargs)

    def list_all(self, **kwargs) -> Page[AttendanceRecord]:
        """Stream every attendance record (used for school-wide analytics)."""
        kwargs.setdefault("order_by", "date")
        return self.list(**kwargs)
