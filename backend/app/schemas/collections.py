from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class StudentProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: str
    name: str
    class_id: Optional[str] = None
    parent_ids: List[str] = []
    roll_number: Optional[str] = None
    is_active: bool = True


class ClassProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    grade: Optional[str] = None
    teacher_id: Optional[str] = None
    student_ids: List[str] = []


class AttendanceRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    student_id: str
    class_id: str
    date: str  # ISO date, e.g. 2026-08-16
    status: str  # PRESENT / ABSENT / LATE
    marked_by: Optional[str] = None


class Conversation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = ""
    user_id: str
    title: Optional[str] = None
    role: Optional[str] = None  # STUDENT / PARENT / TEACHER / PRINCIPAL
    language: Optional[str] = None  # e.g. "en-IN"
    metadata: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = ""
    role: str  # user | assistant | system | tool
    content: str
    timestamp: Optional[datetime] = None
    intent: Optional[str] = None
    entities: Dict[str, Any] = {}
    tool_calls: List[Any] = []
    tool_results: List[Any] = []
    metadata: Dict[str, Any] = {}


class SupportRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: str
    subject: str
    message: str
    status: str = "OPEN"  # OPEN / IN_PROGRESS / RESOLVED
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    actor_id: str
    action: str
    target: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: Optional[datetime] = None
