import hashlib
import hmac
from typing import Optional, Protocol, runtime_checkable

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.vapi.errors import VapiWebhookError

logger = get_logger("app.providers.vapi.verifier")

# Header Vapi uses to carry the HMAC-SHA256 signature of the raw request body.
VAPI_SIGNATURE_HEADER = "X-Vapi-Signature"


@runtime_checkable
class VapiWebhookVerifier(Protocol):
    """Adapter interface for authenticating inbound Vapi webhooks.

    Keeps the external Vapi signing scheme behind an interface so the rest of
    the app depends on this contract, not on a concrete implementation.
    """

    def verify(self, raw_body: bytes, signature: Optional[str]) -> None:
        """Raise `VapiWebhookError` if the request is not authentic."""
        ...


class VapiSignatureVerifier:
    """HMAC-SHA256 verifier using the configured webhook secret.

    Vapi signs the raw request body with the webhook secret; the signature is
    delivered in the `X-Vapi-Signature` header. Comparison is constant-time.
    """

    def __init__(self, secret: Optional[str] = None) -> None:
        self.secret = secret if secret is not None else settings.VAPI_WEBHOOK_SECRET

    def verify(self, raw_body: bytes, signature: Optional[str]) -> None:
        if not self.secret:
            # Fail closed: a production deployment must configure the secret.
            raise VapiWebhookError(
                "Vapi webhook secret is not configured",
                code="WEBHOOK_UNCONFIGURED",
                status_code=500,
            )
        if not signature:
            raise VapiWebhookError(
                "Missing webhook signature", code="UNAUTHORIZED", status_code=401
            )

        expected = hmac.new(
            self.secret.encode("utf-8"), raw_body or b"", hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            # Never log the body or signature — they may contain user content.
            logger.warning("VAPI_WEBHOOK_REJECTED invalid signature")
            raise VapiWebhookError(
                "Invalid webhook signature", code="UNAUTHORIZED", status_code=401
            )


class NoopVerifier:
    """Accepts any webhook. Use only for local development / tests."""

    def verify(self, raw_body: bytes, signature: Optional[str]) -> None:
        return None


# Module-level verifier holder. Tests inject a `NoopVerifier` via
# set_vapi_webhook_verifier(); production uses the HMAC verifier.
_verifier: Optional[VapiWebhookVerifier] = None


def set_vapi_webhook_verifier(verifier: Optional[VapiWebhookVerifier]) -> None:
    global _verifier
    _verifier = verifier


def get_vapi_webhook_verifier() -> VapiWebhookVerifier:
    global _verifier
    if _verifier is None:
        if settings.VAPI_WEBHOOK_VERIFY and settings.VAPI_WEBHOOK_SECRET:
            _verifier = VapiSignatureVerifier()
        else:
            # Development fallback: no verification. Logs loudly.
            logger.warning(
                "Vapi webhook signature verification is DISABLED "
                "(VAPI_WEBHOOK_VERIFY=false or no secret set)"
            )
            _verifier = NoopVerifier()
    return _verifier
