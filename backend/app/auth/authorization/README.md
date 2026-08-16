# Section 05 — Authorization Engine

The application-level **authorization** engine: the final authority on *"what are
you allowed to do?"* (authentication — *who are you?* — is Section 02).

This engine is the authority. The LLM (and any client input) is **never** the
final authorization decision.

## Context (`app.auth.authorization.context`)

```python
AuthorizationContext:
    user_id, firebase_uid
    role: Role                 # STUDENT / PARENT / TEACHER / PRINCIPAL
    active: bool
    relationship: RelationshipData
        student_id?, child_ids[], class_ids[], authorized_student_ids[], school_wide
```

The context is built **only** from the stored Firestore identity:

- `build_authorization_context(profile)` — from an authoritative `UserProfile`.
- `get_authorization_context(authenticated_user)` — loads the profile by Firebase
  UID via the Section 03 service, so the role is never read from the token.

Because the role/active/relationship come solely from the stored profile, a
client-supplied or LLM-supplied role claim cannot widen access.

## Policy functions (`app.auth.authorization.policies`)

Each returns a structured `AuthorizationResult(allowed, code?, message?)` and
**never leaks internal relationship data** in its message:

```python
can_view_own_attendance(context)
can_view_child_attendance(context, child_id)
can_mark_attendance(context, student_id)
can_view_school_analytics(context)
can_create_teacher_escalation(context, student_id)
can_create_management_escalation(context)
```

| Role | Allowed | Denied |
| --- | --- | --- |
| STUDENT | own attendance | child attendance, marking, analytics |
| PARENT | own children's attendance, child escalation | unrelated child, marking, principal analytics |
| TEACHER | authorized classes/students, marking, teacher escalation | unrelated classes/students |
| PRINCIPAL | school-wide analytics, management escalation | — |

`enforce(result)` raises `AppError("FORBIDDEN", ..., 403)` (standardized error)
when a check fails — call it inside routes/services.

## Usage

```python
from app.auth.authorization import get_authorization_context, can_mark_attendance, enforce

ctx = get_authorization_context(authenticated_user)
enforce(can_mark_attendance(ctx, student_id))
# ... perform the (now authorized) action ...
```

## Security guarantees
- Role/active/relationships are read only from the stored profile (Sections 03/04).
- No raw Firestore access here — relies on the user service and repositories.
- Denials return a generic reason; relationship scope is not exposed.
- Inactive users are denied everywhere.

## Tests
`tests/test_authorization.py` covers every role against allowed, denied,
unrelated-resource, fake-role-claim, and inactive-user cases, plus context
scoping, `enforce()`, and the stored-identity loader.
