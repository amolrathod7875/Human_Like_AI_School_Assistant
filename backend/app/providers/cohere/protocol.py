from typing import Any, Protocol, runtime_checkable

from app.providers.cohere.models import LLMRequest, LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    """Adapter interface for LLM providers.

    The rest of the project depends on this contract, never on the Cohere SDK.
    """

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a completion/response for the given request."""
        ...
