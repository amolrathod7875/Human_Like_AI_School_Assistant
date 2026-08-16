# Section 04 — Firestore Repository Layer

Generic, typed data-access layer over Firestore. This is the **only** place raw
Firestore SDK calls live. No API route and no AI tool should contain raw
Firestore code — they go through a repository from this module.

## Provider

```python
from app.providers.firestore_provider import get_firestore_client
```

`get_firestore_client()` returns the shared Firestore client, initializing
Firebase once (via `app.providers.firebase_provider.get_firebase_app()`).

## Generic base — `app.repositories.base`

`FirestoreRepository[T]` (Pydantic-bounded generic) provides typed CRUD plus:

- `get(doc_id)` → `Optional[T]`
- `create(model, doc_id=None)` → `T` (auto-id when `doc_id` is `None`)
- `update(doc_id, changes)` → partial update
- `delete(doc_id)`
- `list(filters=..., order_by=..., page_size=20, start_after=...)` → `Page[T]`
- document ⇄ model mapping, `created_at`/`updated_at` server timestamps
- cursor pagination with opaque `next_page_token`
- error mapping via `map_firestore_error()` → `RepositoryError(code, message, status_code)`

`Page[T]` = `dataclass(items, next_page_token)`.

### Critical rule
The base contains **no business rules**. It does not decide authorization
(e.g. "is this parent allowed to see this child"). That belongs to services.

## Concrete repositories

| Repository | Collection | Extras |
| --- | --- | --- |
| `UserRepository` | `users` | `get_by_id`, `get_by_firebase_uid` (shared with Section 03) |
| `StudentRepository` | `students` | `list_by_class`, `list_by_parent` |
| `ClassRepository` | `classes` | `list_by_teacher` |
| `AttendanceRepository` | `attendance` | `list_by_student`, `list_by_class` |
| `ConversationRepository` | `conversations` | `list_by_user` |
| `SupportRequestRepository` | `support_requests` | `list_by_user`, `list_by_status` |
| `AuditLogRepository` | `audit_logs` | `record(...)` helper |

Each repository only implements the CRUD methods its collection needs.

## Collection models
Pydantic models for non-user collections live in `app/schemas/collections.py`
(`StudentProfile`, `ClassProfile`, `AttendanceRecord`, `Conversation`,
`SupportRequest`, `AuditLog`). `UserProfile` remains in `app/schemas/user.py`.

## Testing
`tests/test_firestore_repository.py` exercises the generic base and every
concrete repository against an in-memory fake Firestore client (correct document
mapping, partial update, delete, filtered queries, cursor pagination, error
mapping). `map_firestore_error` is verified against the SDK exception types.
