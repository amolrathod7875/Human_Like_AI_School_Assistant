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

## Attendance Domain (`app.services.attendance_service`)

The primary school domain: reading and marking attendance, and school-wide
analytics. Backed by the Firestore `attendance` collection (`AttendanceRecord`).

### Status values
`PRESENT`, `ABSENT`, `LATE` (see `app.schemas.attendance.AttendanceStatus`).

### Service interface

```python
resolve_student_reference(*, name=None, student_id=None) -> StudentAmbiguity
get_student_attendance(context, student_id, date_range=None) -> list[AttendanceRecord]
get_child_attendance(context, child_id, date_range=None)    -> list[AttendanceRecord]
mark_attendance(context, student_id, date, status)          -> AttendanceRecord
get_overall_attendance(context, date_range=None)            -> AttendanceSummary
```

### Authorization (Section 05 policies, never duplicated in routes)
- `get_student_attendance`: a `STUDENT` may read **only their own** record
  (id must equal `context.relationship.student_id`); a `PARENT` may read an
  authorized child (`can_view_child_attendance`); everyone else is denied.
- `get_child_attendance`: `PARENT` only, enforced via `can_view_child_attendance`.
- `mark_attendance`: `TEACHER` only, for students in their authorized classes
  (`can_mark_attendance`). `teacher_id` is taken from the stored identity, never
  the request body (Rule 10).
- `get_overall_attendance`: `PRINCIPAL` only (`can_view_school_analytics`).

### Name resolution / ambiguity
`resolve_student_reference` maps a `name` (or `student_id`) to a single student.
If a name matches more than one student it returns `ambiguous=True` with the
candidate list (`StudentAmbiguity`) so callers never guess. The AI tool adapters
reject ambiguous/unknown names with a clear `InvalidArgumentsError`.

### Write behavior
`mark_attendance` upserts: if a record already exists for
(`student_id`, `date`) it updates `status`/`marked_by`; otherwise it creates one
using the student's `class_id`.

### Injection
- `set_attendance_repository` / `get_attendance_repository` (`AttendanceRepository`).
- `set_student_repository` / `get_student_repository` (used for class lookup and
  name resolution).
- Tests inject fakes via these setters.

`tests/test_attendance_service.py` covers name resolution (id passthrough, single,
ambiguous, unknown), student-own / parent-child / teacher-mark / principal-analytics
paths, unauthorized denials, upsert behavior, missing-student and missing-date
handling.

### AI tool adapters (`app.ai.tools.attendance_tools`)
Four `BaseTool` adapters wrap the service and reuse the same Section 05 policies in
their `authorize` hook: `get_own_attendance`, `get_child_attendance`,
`get_overall_attendance`, `mark_attendance`. They are registered at startup via
`bootstrap_tools()` (called from the app lifespan). `get_child_attendance` and
`mark_attendance` accept either `student_id` or `name` and resolve via
`resolve_student_reference`. See `tests/test_attendance_tools.py`.

### API (`app.api.v1.attendance`)
- `GET  /api/v1/attendance/student/{student_id}` — own (student) / child (parent).
- `POST /api/v1/attendance` — mark attendance (teacher). Body: `student_id`,
  `date`, `status` (and optional `name`).
- `GET  /api/v1/attendance/analytics/overall` — school-wide summary (principal).

All routes resolve the caller's `AuthorizationContext` from the verified Firebase
token; authorization is enforced in the service layer. See
`tests/test_attendance_api.py`.

### Escalation / human-support service (pp.services.escalation_service)

Section 13 — teacher/management support-request workflow. Persists to the
support_requests collection (schema in pp.schemas.collections.SupportRequest)
with status PENDING → CONFIRMED | FAILED | CANCELLED, and dispatches to a
human-support adapter. The adapter is behind the HumanSupportAdapter protocol;
the default MockHumanSupportAdapter returns CONFIRMED (no paid provider). The
service enforces Section 05 policies (can_create_teacher_escalation =
parent→own child's teacher or teacher→their student; can_create_management_escalation
= teacher/principal) and only stores the status the adapter returns.

Service interface:

`python
await request_teacher_contact(context, student_id, reason) -> SupportRequest
await request_management_contact(context, reason, student_id=None) -> SupportRequest
await get_request(request_id, context) -> SupportRequest  # owner or principal
`


equest_teacher_contact / 
equest_management_contact raise AppError(FORBIDDEN)
when the policy denies. get_request allows the requester or any principal and
raises NOT_FOUND / FORBIDDEN otherwise. The persisted status is the single
source of truth the AI may relay: only CONFIRMED justifies saying a human was
contacted.

### API (pp.api.v1.escalation)
- POST /api/v1/escalation/request — body { target_type: TEACHER|MANAGEMENT,
  reason, student_id? }. Returns the created request and status.
- GET  /api/v1/escalation/{request_id} — request status (owner or principal).

Tests: 	ests/test_escalation_service.py, 	ests/test_escalation_api.py.
