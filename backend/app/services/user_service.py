from typing import List, Optional

from app.repositories.user_repository import get_user_repository
from app.schemas.user import Role, UserProfile


def get_user_by_firebase_uid(firebase_uid: str) -> Optional[UserProfile]:
    """Load a user profile by its Firebase UID."""
    return get_user_repository().get_by_firebase_uid(firebase_uid)


def get_user_by_id(user_id: str) -> Optional[UserProfile]:
    """Load a user profile by its application id (Firestore document id)."""
    return get_user_repository().get_by_id(user_id)


def get_user_role(user_id: str) -> Optional[Role]:
    """Return the user's role.

    The role is taken ONLY from the stored profile (Firestore). It is never
    read from a client parameter, request body, token claim, or LLM output.
    """
    profile = get_user_by_id(user_id)
    return profile.role if profile else None


def get_children_for_parent(parent_id: str) -> List[UserProfile]:
    """Resolve a parent's children to full profiles."""
    parent = get_user_by_id(parent_id)
    if parent is None:
        return []
    children: List[UserProfile] = []
    for child_id in parent.child_ids:
        child = get_user_by_id(child_id)
        if child is not None:
            children.append(child)
    return children


def get_teacher_classes(teacher_id: str) -> List[str]:
    """Return the class ids assigned to a teacher."""
    teacher = get_user_by_id(teacher_id)
    if teacher is None:
        return []
    return list(teacher.teacher_class_ids)


def is_active_user(user_id: str) -> bool:
    """True only when the stored profile exists and is active.

    Callers must use this (or check `profile.is_active`) to reject inactive
    users; the role/identity store is the sole authority.
    """
    profile = get_user_by_id(user_id)
    return profile is not None and profile.is_active
