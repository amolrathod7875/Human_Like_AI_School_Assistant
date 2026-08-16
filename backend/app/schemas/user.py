from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class Role(str, Enum):
    STUDENT = "STUDENT"
    PARENT = "PARENT"
    TEACHER = "TEACHER"
    PRINCIPAL = "PRINCIPAL"


class UserProfile(BaseModel):
    """Application-level user profile stored in Firestore (`users` collection).

    The document id is the application `id`. The `role` is always the value
    stored in Firestore — it is never taken from a client, token, or LLM.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    firebase_uid: str
    name: str
    email: Optional[str] = None
    role: Role = Role.STUDENT
    is_active: bool = True

    # Relationships
    student_id: Optional[str] = None
    parent_ids: List[str] = []
    class_id: Optional[str] = None
    child_ids: List[str] = []
    teacher_class_ids: List[str] = []
