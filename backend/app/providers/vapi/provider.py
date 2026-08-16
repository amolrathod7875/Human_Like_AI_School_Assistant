import json
from typing import Any, Optional

from app.core.config import settings
from app.providers.vapi.errors import VapiError
from app.providers.vapi.models import NormalizedVoiceEvent
from app.providers.vapi.normalizer import normalize_event, normalize_response
from app.providers.vapi.verifier import (
    VapiWebhookVerifier,
    get_vapi_webhook_verifier,
)


class VapiAdapter:
    """Provider/adapter boundary for Vapi voice.

    Responsibilities (this layer only):
    - authenticate inbound webhooks (HMAC signature via the verifier)
    - normalize raw Vapi payloads into `NormalizedVoiceEvent`
    - serialize orchestrator responses back into Vapi's `results` shape

    It deliberately contains NO business rules or authorization logic. The
    orchestrator (and its authorization engine) owns those; this adapter only
    adapts the wire format.
    """

    def __init__(
        self,
        verifier: Optional[VapiWebhookVerifier] = None,
        voice_tool_name: Optional[str] = None,
    ) -> None:
        self._verifier = verifier
        self.voice_tool_name = voice_tool_name or settings.VAPI_VOICE_TOOL_NAME

    @property
    def verifier(self) -> VapiWebhookVerifier:
        if self._verifier is None:
            self._verifier = get_vapi_webhook_verifier()
        return self._verifier

    def parse(self, raw_body: bytes, signature: Optional[str]) -> NormalizedVoiceEvent:
        """Verify and normalize a raw webhook request body."""
        self.verifier.verify(raw_body, signature)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise VapiError(
                "Could not parse webhook body", code="INVALID_EVENT", status_code=400
            ) from exc
        return normalize_event(payload, voice_tool_name=self.voice_tool_name)

    def respond(self, event: NormalizedVoiceEvent, chat_response: Any) -> dict:
        """Serialize an orchestrator response into Vapi's reply shape."""
        return normalize_response(
            event, chat_response, voice_tool_name=self.voice_tool_name
        )


# Module-level adapter holder. Tests inject a configured adapter (e.g. with a
# NoopVerifier) via set_vapi_adapter(); production uses the default adapter.
_adapter: Optional[VapiAdapter] = None


def set_vapi_adapter(adapter: Optional[VapiAdapter]) -> None:
    global _adapter
    _adapter = adapter


def get_vapi_adapter() -> VapiAdapter:
    global _adapter
    if _adapter is None:
        _adapter = VapiAdapter()
    return _adapter
