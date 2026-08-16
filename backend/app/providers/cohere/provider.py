import asyncio
import json
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.providers.cohere.errors import LLMProviderError
from app.providers.cohere.models import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolDefinition,
)

# Map Cohere finish reasons -> application-level reasons.
_FINISH_REASON_MAP = {
    "COMPLETE": "STOP",
    "TOOL_CALL": "TOOL_CALL",
    "MAX_TOKENS": "MAX_TOKENS",
    "ERROR": "ERROR",
}


def _is_retryable(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status in (429, 500, 502, 503):
        return True
    name = type(exc).__name__.lower()
    return "timeout" in name or "connection" in name


class CohereProvider:
    """Cohere-backed implementation of `LLMProvider`.

    This is the ONLY module that imports the Cohere SDK. The blocking SDK call
    is run in a thread so `generate` can stay async. API key, model, timeout,
    and retries come from settings (or constructor overrides). The client is
    lazy and injectable for tests.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        client: Any = None,
    ) -> None:
        self.api_key = api_key or settings.COHERE_API_KEY
        self.model = model or settings.COHERE_MODEL
        self.timeout = timeout if timeout is not None else settings.COHERE_TIMEOUT
        self.max_retries = (
            max_retries if max_retries is not None else settings.COHERE_MAX_RETRIES
        )
        self._client = client

    @property
    def client(self):
        if self._client is None:
            import cohere

            self._client = cohere.ClientV2(
                api_key=self.api_key, timeout=self.timeout
            )
        return self._client

    # ---- public API ----
    async def generate(self, request: LLMRequest) -> LLMResponse:
        kwargs = self._build_kwargs(request)
        last_error: Optional[LLMProviderError] = None

        for attempt in range(self.max_retries + 1):
            try:
                raw = await asyncio.to_thread(self._call_sync, kwargs)
                return self._to_response(raw)
            except LLMProviderError as exc:
                last_error = exc
                if not exc.retryable or attempt >= self.max_retries:
                    break

        raise last_error or LLMProviderError("LLM generation failed")

    # ---- request building ----
    def _build_kwargs(self, request: LLMRequest) -> Dict[str, Any]:
        system = self._build_system(request)
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
        ]
        tools = self._build_tools(request.tool_definitions)

        kwargs: Dict[str, Any] = {
            "model": request.model or self.model,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        return kwargs

    def _build_system(self, request: LLMRequest) -> str:
        parts: List[str] = []
        if request.system_instructions:
            parts.append(request.system_instructions)
        if request.persona_instruction:
            parts.append(f"Persona: {request.persona_instruction}")
        if request.language_instruction:
            parts.append(f"Language: {request.language_instruction}")
        if request.user_context:
            try:
                ctx = json.dumps(request.user_context, ensure_ascii=False)
            except (TypeError, ValueError):
                ctx = str(request.user_context)
            parts.append(f"Context: {ctx}")
        return "\n\n".join(parts)

    @staticmethod
    def _build_tools(
        definitions: Optional[List[LLMToolDefinition]],
    ) -> List[Dict[str, Any]]:
        if not definitions:
            return []
        return [
            {
                "type": "function",
                "function": {
                    "name": d.name,
                    "description": d.description,
                    "parameters": d.parameters,
                },
            }
            for d in definitions
        ]

    # ---- transport ----
    def _call_sync(self, kwargs: Dict[str, Any]):
        try:
            return self.client.chat(**kwargs)
        except Exception as exc:  # normalize all SDK/transport errors
            raise self._wrap_error(exc) from exc

    @staticmethod
    def _wrap_error(exc: Exception) -> LLMProviderError:
        status = getattr(exc, "status_code", None)
        return LLMProviderError(
            f"Cohere request failed: {type(exc).__name__}",
            retryable=_is_retryable(exc),
            status_code=status,
        )

    # ---- response mapping ----
    def _to_response(self, raw: Any) -> LLMResponse:
        message = getattr(raw, "message", None)
        if message is None:
            raise LLMProviderError(
                "Malformed LLM response: missing 'message'", retryable=False
            )

        text = self._extract_text(message)
        tool_calls = self._extract_tool_calls(message)

        fr = getattr(raw, "finish_reason", None) or getattr(
            message, "finish_reason", None
        )
        finish = _FINISH_REASON_MAP.get(fr, fr)

        return LLMResponse(text=text, tool_calls=tool_calls, finish_reason=finish)

    @staticmethod
    def _extract_text(message: Any) -> Optional[str]:
        content = getattr(message, "content", None)
        if content is None:
            return None
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return None

        parts: List[str] = []
        for block in content:
            block_type = (
                block.get("type")
                if isinstance(block, dict)
                else getattr(block, "type", None)
            )
            if block_type == "text":
                text = (
                    block.get("text")
                    if isinstance(block, dict)
                    else getattr(block, "text", "")
                )
                if text:
                    parts.append(text)
        return "".join(parts) if parts else None

    @staticmethod
    def _extract_tool_calls(message: Any) -> List[LLMToolCall]:
        raw_tools = getattr(message, "tool_calls", None) or []
        calls: List[LLMToolCall] = []
        for tc in raw_tools:
            func = getattr(tc, "function", None)
            name = getattr(func, "name", None) if func else None
            args = getattr(func, "arguments", {}) if func else {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (TypeError, ValueError):
                    args = {}
            calls.append(
                LLMToolCall(id=getattr(tc, "id", None), name=name, arguments=args or {})
            )
        return calls


# Module-level provider holder. Tests inject a MockLLMProvider via
# set_llm_provider(); production code receives the default CohereProvider.
_provider = None


def set_llm_provider(provider) -> None:
    global _provider
    _provider = provider


def get_llm_provider():
    global _provider
    if _provider is None:
        _provider = CohereProvider()
    return _provider
