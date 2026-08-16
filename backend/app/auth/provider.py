from typing import Any, Dict, Optional, Protocol, runtime_checkable

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.auth.provider")


class TokenVerificationError(Exception):
    """Raised when a Firebase ID token cannot be verified.

    Callers map this to a 401 Unauthorized response. The message never
    contains the raw token.
    """


@runtime_checkable
class TokenVerifier(Protocol):
    """Adapter interface for verifying ID tokens.

    Keeps the external Firebase provider behind an interface so the rest of
    the app depends on this contract, not on firebase-admin directly.
    """

    def verify_id_token(self, token: str) -> Dict[str, Any]:
        """Return decoded claims for a valid token, else raise TokenVerificationError."""
        ...


class FirebaseTokenVerifier:
    """Token verifier backed by the Firebase Admin SDK.

    The SDK is imported lazily so the application can import this module
    without firebase-admin installed (e.g. in unit tests with a fake verifier).
    """

    _app = None  # type: ignore[var-annotated]

    def verify_id_token(self, token: str) -> Dict[str, Any]:
        try:
            import firebase_admin
            from firebase_admin import auth as firebase_auth
            from firebase_admin import credentials as fb_credentials
        except ImportError as exc:  # pragma: no cover - SDK optional in tests
            raise TokenVerificationError(
                "Firebase Admin SDK is not installed"
            ) from exc

        if FirebaseTokenVerifier._app is None:
            FirebaseTokenVerifier._app = self._initialize(
                firebase_admin, fb_credentials
            )

        try:
            # Do NOT log the token. Only a non-identifying summary is logged.
            return firebase_auth.verify_id_token(
                token, app=FirebaseTokenVerifier._app
            )
        except Exception as exc:
            logger.warning("Token verification failed: %s", type(exc).__name__)
            raise TokenVerificationError(str(exc)) from exc

    @staticmethod
    def _initialize(firebase_admin, fb_credentials):  # type: ignore[no-untyped-def]
        project_id = settings.FIREBASE_PROJECT_ID
        client_email = settings.FIREBASE_CLIENT_EMAIL
        private_key = settings.FIREBASE_PRIVATE_KEY

        if private_key:
            # Env vars often escape newlines as literal "\n".
            private_key = private_key.replace("\\n", "\n")

        if project_id and client_email and private_key:
            credential = fb_credentials.Certificate(
                {
                    "type": "service_account",
                    "project_id": project_id,
                    "client_email": client_email,
                    "private_key": private_key,
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            )
            return firebase_admin.initialize_app(credential)

        # Secure fallback: use ambient credentials
        # (e.g. GOOGLE_APPLICATION_CREDENTIALS) for the deployed environment.
        logger.info(
            "Initializing Firebase with application default credentials"
        )
        return firebase_admin.initialize_app()


# Module-level verifier holder. Tests can swap in a fake verifier via
# set_token_verifier(). Production code uses the Firebase implementation.
_verifier: Optional[TokenVerifier] = None


def set_token_verifier(verifier: Optional[TokenVerifier]) -> None:
    """Override the active token verifier (used by tests and custom providers)."""
    global _verifier
    _verifier = verifier


def get_token_verifier() -> TokenVerifier:
    """Return the active token verifier, defaulting to Firebase."""
    global _verifier
    if _verifier is None:
        _verifier = FirebaseTokenVerifier()
    return _verifier
