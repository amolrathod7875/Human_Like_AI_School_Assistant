from typing import Annotated, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.context import AuthenticatedUser
from app.auth.provider import TokenVerificationError, get_token_verifier
from app.core.errors import AppError

# auto_error=False so we control the response (401 instead of 403).
bearer_scheme = HTTPBearer(auto_error=False)


async def get_authenticated_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
) -> AuthenticatedUser:
    """Reusable FastAPI dependency that returns the verified caller.

    Security:
    - Missing bearer token -> 401.
    - Any verification failure (malformed/expired/invalid/revoked) -> 401.
    - Identity (firebase_uid) is taken ONLY from the verified token claims.
      A client-supplied UID is never trusted as authoritative.
    - Role claims are intentionally NOT read here (owned by later sections).
    """
    if credentials is None or not credentials.credentials:
        raise AppError(
            "Missing bearer token", "UNAUTHORIZED", status_code=401
        )

    try:
        claims = get_token_verifier().verify_id_token(credentials.credentials)
    except TokenVerificationError as exc:
        raise AppError(
            "Invalid or expired token", "UNAUTHORIZED", status_code=401
        ) from exc

    uid = claims.get("uid")
    if not uid:
        raise AppError(
            "Token is missing a subject", "UNAUTHORIZED", status_code=401
        )

    return AuthenticatedUser(
        firebase_uid=uid,
        email=claims.get("email"),
        name=claims.get("name"),
    )
