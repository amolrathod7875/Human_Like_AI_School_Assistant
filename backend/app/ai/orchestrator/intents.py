from enum import Enum
from typing import Dict, FrozenSet, Iterable, List, Tuple

from app.schemas.user import Role


class Intent(str, Enum):
    """Intents the orchestrator understands.

    Anything the model returns that is not in this enum is normalized to
    `GENERAL_QUERY` — the model can never widen this list at runtime.
    """

    VIEW_OWN_ATTENDANCE = "VIEW_OWN_ATTENDANCE"
    VIEW_CHILD_ATTENDANCE = "VIEW_CHILD_ATTENDANCE"
    MARK_ATTENDANCE = "MARK_ATTENDANCE"
    VIEW_SCHOOL_ATTENDANCE = "VIEW_SCHOOL_ATTENDANCE"
    REQUEST_TEACHER_CONTACT = "REQUEST_TEACHER_CONTACT"
    REQUEST_MANAGEMENT_CONTACT = "REQUEST_MANAGEMENT_CONTACT"
    GENERAL_QUERY = "GENERAL_QUERY"


# Entity keys the orchestrator accepts from the model. Everything else (notably
# any role/permission claim) is dropped before use or persistence.
ENTITY_KEYS: FrozenSet[str] = frozenset(
    {
        "student_name",
        "student_id",
        "date",
        "date_range",
        "class_id",
        "reason",
    }
)

# Keys that would be an attempt to influence identity/authorization through the
# model output. They are dropped and logged as a security event.
FORBIDDEN_ENTITY_KEYS: FrozenSet[str] = frozenset(
    {
        "role",
        "roles",
        "user_id",
        "firebase_uid",
        "permissions",
        "scope",
        "school_wide",
        "is_admin",
        "authorized_student_ids",
        "child_ids",
    }
)

# Which tools may satisfy an intent. Purely advisory for prompting/telemetry:
# the tool registry allowlist and the authorization engine remain authoritative.
INTENT_TOOLS: Dict[Intent, Tuple[str, ...]] = {
    Intent.VIEW_OWN_ATTENDANCE: ("get_own_attendance",),
    Intent.VIEW_CHILD_ATTENDANCE: ("get_child_attendance",),
    Intent.MARK_ATTENDANCE: ("mark_attendance",),
    Intent.VIEW_SCHOOL_ATTENDANCE: ("get_overall_attendance",),
    # Owned by Section 13 (escalation); may not be registered yet.
    Intent.REQUEST_TEACHER_CONTACT: ("create_teacher_contact_request",),
    Intent.REQUEST_MANAGEMENT_CONTACT: ("create_management_contact_request",),
    Intent.GENERAL_QUERY: (),
}

# Intents that need a uniquely resolved student before any action is possible.
STUDENT_REFERENCE_INTENTS: FrozenSet[Intent] = frozenset(
    {Intent.VIEW_CHILD_ATTENDANCE, Intent.MARK_ATTENDANCE}
)

# Attendance tools this module knows how to scope per role. Defense in depth for
# prompting only — it reduces what the model is even offered.
ROLE_TOOLS: Dict[Role, Tuple[str, ...]] = {
    Role.STUDENT: ("get_own_attendance",),
    Role.PARENT: ("get_child_attendance", "create_teacher_contact_request"),
    Role.TEACHER: ("mark_attendance", "create_teacher_contact_request",
                   "create_management_contact_request"),
    Role.PRINCIPAL: ("get_overall_attendance", "create_management_contact_request"),
}

_SCOPED_TOOLS: FrozenSet[str] = frozenset(
    name for names in ROLE_TOOLS.values() for name in names
)


def normalize_intent(value) -> Intent:
    """Map arbitrary model output to a known intent (`GENERAL_QUERY` fallback)."""
    if isinstance(value, Intent):
        return value
    try:
        return Intent(str(value).strip().upper())
    except (ValueError, AttributeError):
        return Intent.GENERAL_QUERY


def tools_for_role(role: Role, available: Iterable[str]) -> List[str]:
    """Filter available tool names down to those relevant for `role`.

    Tools this module does not scope (e.g. tools owned by other sections) are
    passed through: their own `authorize()` hook and policies decide. This is a
    prompt-shaping filter, never the authorization decision.
    """
    allowed = set(ROLE_TOOLS.get(role, ()))
    return [
        name
        for name in available
        if name in allowed or name not in _SCOPED_TOOLS
    ]
