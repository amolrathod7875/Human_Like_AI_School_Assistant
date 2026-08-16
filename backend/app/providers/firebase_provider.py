from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.providers.firebase")

# Initialized once and reused. Both the auth verifier and Firestore repository
# obtain the app through this function to avoid double-initialization errors.
_app: Any = None


def get_firebase_app() -> Any:
    """Return the initialized Firebase app, initializing it on first use.

    Credentials are taken from environment / secret manager (never hardcoded).
    When the explicit service-account vars are absent, application default
    credentials (e.g. GOOGLE_APPLICATION_CREDENTIALS) are used instead.
    """
    global _app
    if _app is not None:
        return _app

    import firebase_admin
    from firebase_admin import credentials as fb_credentials

    project_id = settings.FIREBASE_PROJECT_ID
    client_email = settings.FIREBASE_CLIENT_EMAIL
    private_key = settings.FIREBASE_PRIVATE_KEY
    if private_key:
        # Env values frequently escape newlines as literal "\n".
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
        _app = firebase_admin.initialize_app(credential)
    else:
        logger.info("Firebase: using application default credentials")
        _app = firebase_admin.initialize_app()

    return _app
