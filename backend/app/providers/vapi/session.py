from typing import Optional, Protocol, runtime_checkable

from app.core.logging import get_logger

logger = get_logger("app.providers.vapi.session")


@runtime_checkable
class VoiceSessionStore(Protocol):
    """Maps a Vapi call id to the backend conversation id for that call."""

    def get(self, call_id: str) -> Optional[str]: ...

    def set(self, call_id: str, conversation_id: str) -> None: ...


class InMemoryVoiceSessionStore:
    """Default session store. Suitable for a single-instance deployment.

    For multi-instance deployments a shared store (e.g. Firestore) should be
    injected via `set_voice_session_store`.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, call_id: str) -> Optional[str]:
        return self._store.get(call_id)

    def set(self, call_id: str, conversation_id: str) -> None:
        self._store[call_id] = conversation_id


# Module-level holder (injectable for tests / alternative stores).
_store: Optional[VoiceSessionStore] = None


def set_voice_session_store(store: Optional[VoiceSessionStore]) -> None:
    global _store
    _store = store


def get_voice_session_store() -> VoiceSessionStore:
    global _store
    if _store is None:
        _store = InMemoryVoiceSessionStore()
    return _store
