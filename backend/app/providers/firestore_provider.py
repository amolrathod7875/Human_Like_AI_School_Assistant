from typing import Any

from app.providers.firebase_provider import get_firebase_app

# Lazily-initialized Firestore client singleton.
_client: Any = None


def get_firestore_client() -> Any:
    """Return the Firestore client, initializing Firebase once if needed.

    This is the single, shared entry point for repository data access. No route
    or AI tool should call the raw Firestore SDK directly — they go through a
    repository that obtains the client from here.
    """
    global _client
    if _client is None:
        from firebase_admin import firestore

        app = get_firebase_app()
        _client = firestore.client(app=app)
    return _client
