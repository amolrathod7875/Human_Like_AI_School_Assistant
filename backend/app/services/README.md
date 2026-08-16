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

## Conversation & Memory Engine (`app.services.conversation_service`)

Stores conversations and makes structured context available to the AI
orchestrator. Conversations live in the `conversations` collection; messages in
the `conversations/{conversation_id}/messages` subcollection (via
`MessageRepository`).

Service functions (each takes the caller's `AuthorizationContext`):

```python
create_conversation(context, language="en-IN", metadata=None) -> Conversation
get_conversation(conversation_id, context)                  -> Conversation
append_message(conversation_id, message, context)           -> Message
get_recent_messages(conversation_id, context, limit=20)     -> list[Message]
build_context(conversation_id, context, limit=20)           -> ConversationContext
```

`ConversationContext` carries `conversation_id`, `recent_messages` (most-recent
first), `language`, aggregated `known_entities`, and `previous_tool_results` so
follow-up questions can rely on prior context.

### Security
- A user may only access **their own** conversations; `PRINCIPAL` (school-wide)
  may access any per the administrative policy. Others get `FORBIDDEN`.
- Ownership is enforced on every read **and** write (append).
- The conversation's `role` is taken from the stored `AuthorizationContext`,
  never from the client.

### Repositories / injection
- `ConversationRepository` (Section 04) backs `conversations`.
- `MessageRepository` (subcollection) backs `messages`; injectable via
  `set_message_repository_factory`.
- `set_conversation_repository` / `set_message_repository_factory` allow tests
  to inject fakes.

`tests/test_conversation_service.py` covers create, append, recent retrieval
(most-recent-first), ownership enforcement (and principal override), and
context generation including the follow-up scenario (entities/tool results
carried into `ConversationContext`).
