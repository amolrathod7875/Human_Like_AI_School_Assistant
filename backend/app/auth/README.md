# Section 02 — Firebase Authentication

Verifies Firebase Authentication ID tokens and exposes the verified caller identity
to the rest of the backend. This module only establishes **authentication** (who the
caller is). **Authorization / roles** are out of scope here (see later sections).

## Interfaces

```python
from app.auth import (
    AuthenticatedUser,        # identity model
    get_authenticated_user,   # FastAPI dependency
    TokenVerifier,            # adapter interface
    FirebaseTokenVerifier,    # default Firebase implementation
    TokenVerificationError,
    get_token_verifier,
    set_token_verifier,
)
```

### `AuthenticatedUser`
```python
class AuthenticatedUser:
    firebase_uid: str
    email: str | None
    name: str | None
```
No application role is included yet (added by Section 03 if needed).

### `get_authenticated_user()`
Reusable FastAPI dependency. Returns `AuthenticatedUser` or raises `AppError`
with code `UNAUTHORIZED` (HTTP 401) on:
- missing bearer token
- malformed / expired / invalid / revoked token
- token missing a subject (`uid`)

## Endpoint

```http
GET /api/v1/auth/me
Authorization: Bearer <firebase_id_token>
```

Response (success):
```json
{
  "success": true,
  "data": { "firebase_uid": "...", "email": "...", "name": "..." }
}
```

## Security rules enforced
- Raw bearer tokens are **never** logged.
- Firebase UID is taken **only** from verified token claims. A client-supplied UID
  is never trusted as authoritative identity.
- Role claims are intentionally not read here.

## Configuration (required env vars)

| Variable | Purpose |
| --- | --- |
| `FIREBASE_PROJECT_ID` | Firebase project id |
| `FIREBASE_CLIENT_EMAIL` | Service-account client email |
| `FIREBASE_PRIVATE_KEY` | Service-account private key (escaped `\n` normalized at runtime) |

If the three values are absent, the SDK falls back to application default
credentials (e.g. `GOOGLE_APPLICATION_CREDENTIALS`) for the deployment environment.

## Provider abstraction
`TokenVerifier` is a `Protocol`. The default `FirebaseTokenVerifier` wraps
`firebase-admin` (imported lazily). Tests (and alternative providers) can inject a
fake via `set_token_verifier(...)`.

## Tests
`tests/test_auth.py` covers valid, invalid, expired (failure path), missing, and
subject-less tokens using an injected fake verifier (no real Firebase needed).
