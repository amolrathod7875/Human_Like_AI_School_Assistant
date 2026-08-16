from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.user import Role, UserProfile


class RelationshipData(BaseModel):
    """Caller-specific relationship scope used by policy decisions.

    This is derived ONLY from the stored profile (never from the client), so it
    cannot be widened by a fake role/claim.
    """

    model_config = ConfigDict(extra="ignore")

    student_id: Optional[str] = None
    child_ids: List[str] = []
    class_ids: List[str] = []
    authorized_student_ids: List[str] = []
    school_wide: bool = False


class AuthorizationContext(BaseModel):
    """The authorization subject: who the caller is and what they can reach.

    `role` and `active` come strictly from the stored Firestore identity.
    """

    model_config = ConfigDict(extra="ignore")

    user_id: str
    firebase_uid: str
    role: Role
    active: bool
    relationship: RelationshipData


class AuthorizationResult(BaseModel):
    """Structured outcome of a policy check."""

    allowed: bool
    code: Optional[str] = None
    message: Optional[str] = None


def build_authorization_context(
    profile: UserProfile, student_repo=None
) -> AuthorizationContext:
    """Build a context from an authoritative (stored) user profile.

    The role/active/relationship values are taken from `profile` only. Any role
    a client might claim in a token is ignored — the stored identity wins.
    """
    rel = RelationshipData()

    if profile.role == Role.STUDENT:
        rel.student_id = profile.student_id
        if profile.student_id:
            rel.authorized_student_ids = [profile.student_id]
        rel.class_ids = [profile.class_id] if profile.class_id else []
    elif profile.role == Role.PARENT:
        rel.child_ids = list(profile.child_ids)
    elif profile.role == Role.TEACHER:
        rel.class_ids = list(profile.teacher_class_ids)
        # Resolve the set of students in the teacher's authorized classes.
        from app.repositories import StudentRepository

        repo = student_repo or StudentRepository()
        authorized: List[str] = []
        for class_id in profile.teacher_class_ids:
            page = repo.list_by_class(class_id, page_size=500)
            authorized.extend(s.id for s in page.items)
        rel.authorized_student_ids = authorized
    elif profile.role == Role.PRINCIPAL:
        rel.school_wide = True

    return AuthorizationContext(
        user_id=profile.id,
        firebase_uid=profile.firebase_uid,
        role=profile.role,
        active=profile.is_active,
        relationship=rel,
    )


def get_authorization_context(authenticated_user) -> AuthorizationContext:
    """Build a context for an authenticated caller (Section 02 user).

    Loads the stored profile by Firebase UID so the role is never taken from the
    token. Raises AppError(FORBIDDEN) when no profile exists.
    """
    from app.core.errors import AppError
    from app.services.user_service import get_user_by_firebase_uid

    profile = get_user_by_firebase_uid(authenticated_user.firebase_uid)
    if profile is None:
        raise AppError("User profile not found", "FORBIDDEN", status_code=403)
    return build_authorization_context(profile)
