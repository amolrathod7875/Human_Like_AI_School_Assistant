# Section 03 — User Profile / Role / Relationship Service

Application-level user profiles, roles, and school relationships, backed by the
Firestore `users` collection. This module owns **identity/role data** only;
authentication (who the caller is) is established by Section 02.

## Roles

`STUDENT`, `PARENT`, `TEACHER`, `PRINCIPAL` (see `app.schemas.user.Role`).

## Firestore

Collection: `users`. Document id = application user id. Example document:

```json
{
  "firebase_uid": "firebase-123",
  "name": "Amit Sharma",
  "email": "amit@example.com",
  "role": "PARENT",
  "student_id": null,
  "child_ids": ["student_001"],
  "teacher_class_ids": [],
  "is_active": true
}
```

Relationship fields on the profile:

| Role | Fields |
| --- | --- |
| Student | `student_id`, `parent_ids`, `class_id` |
| Parent | `child_ids` |
| Teacher | `teacher_class_ids` |
| Principal | school-wide access (no extra fields) |

## Service interface (`app.services.user_service`)

```python
get_user_by_firebase_uid(firebase_uid) -> UserProfile | None
get_user_by_id(user_id)             -> UserProfile | None
get_user_role(user_id)              -> Role | None
get_children_for_parent(parent_id)  -> list[UserProfile]
get_teacher_classes(teacher_id)     -> list[str]
is_active_user(user_id)             -> bool
```

## Critical security rule

The role is **never** trusted from: frontend, query params, request body, LLM, or
tool arguments. `get_user_role` reads the role only from the stored profile. A
caller must use `is_active_user()` (or `profile.is_active`) to reject inactive
users.

## Provider abstraction

`UserRepository` is a `Protocol`. The default `FirestoreUserRepository` wraps
firebase-admin (imported lazily). Tests inject a fake via
`set_user_repository(...)`. Firebase initialization is shared via
`app.providers.firebase_provider.get_firebase_app()` (used by both the auth
verifier and this repository) so the app is initialized only once.

## Tests

`tests/test_user_service.py` covers: each role loads correctly, parent–child
resolution, teacher–class resolution, inactive-user rejection, stored role not
overridable by a fake value, and lookup by Firebase UID (all via a fake repo).
