from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"


class DateRange(BaseModel):
    """Inclusive date range (ISO `YYYY-MM-DD`). Either bound is optional."""

    model_config = ConfigDict(extra="ignore")

    start_date: Optional[str] = None
    end_date: Optional[str] = None


class MarkAttendanceInput(BaseModel):
    """Payload for marking a single student's attendance on a date."""

    model_config = ConfigDict(extra="ignore")

    student_id: Optional[str] = None
    name: Optional[str] = None  # resolved to student_id; ambiguity yields an error
    date: str  # ISO date, e.g. 2026-08-16
    status: AttendanceStatus


class AttendanceSummary(BaseModel):
    """Aggregated attendance statistics across the school (or a scope)."""

    model_config = ConfigDict(extra="ignore")

    total: int = 0
    present: int = 0
    absent: int = 0
    late: int = 0
    attendance_rate: float = 0.0  # present / total, as a percentage


class StudentCandidate(BaseModel):
    """A possible match when resolving a student by name."""

    model_config = ConfigDict(extra="ignore")

    student_id: str
    name: str
    class_id: Optional[str] = None


class StudentAmbiguity(BaseModel):
    """Result of resolving a student reference (id or name).

    `ambiguous` is True when a name matched more than one student. In that case
    `candidates` lists the matches and the caller must disambiguate rather than
    guess which student was meant.
    """

    model_config = ConfigDict(extra="ignore")

    resolved_id: Optional[str] = None
    ambiguous: bool = False
    candidates: List[StudentCandidate] = []
