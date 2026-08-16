from typing import List, Optional

from app.providers.cohere.models import LLMRequest, LLMResponse


class MockLLMProvider:
    """Test/double LLM provider. Returns scripted or fixed responses.

    Implements the `LLMProvider` contract so it can be injected anywhere the
    real `CohereProvider` would be used.
    """

    def __init__(
        self,
        response: Optional[LLMResponse] = None,
        responses: Optional[List[LLMResponse]] = None,
    ) -> None:
        self._responses = list(responses) if responses else None
        self._default = response or LLMResponse(
            text="mock response", finish_reason="STOP"
        )
        self.calls: List[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        if self._responses:
            return self._responses.pop(0)
        return self._default
