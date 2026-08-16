import json
import re
from typing import Any, Dict, List, Optional

from app.ai.orchestrator.intents import (
    ENTITY_KEYS,
    FORBIDDEN_ENTITY_KEYS,
    normalize_intent,
)
from app.ai.orchestrator.schemas import ModelDecision, ProposedToolCall
from app.core.logging import get_logger
from app.providers.cohere.models import LLMResponse

logger = get_logger("app.ai.orchestrator.validation")

# Shape limits for anything coming out of the model.
_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")
_MAX_TEXT_LENGTH = 2000
_MAX_ENTITY_VALUE_LENGTH = 200
_MAX_ARGUMENT_KEYS = 20


def extract_json_object(text: Optional[str]) -> Optional[Dict[str, Any]]:
    """Pull the first balanced JSON object out of model text.

    Tolerates code fences and surrounding prose. Returns `None` when the text is
    not (or does not contain) a JSON object.
    """
    if not text:
        return None

    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-zA-Z]*\s*", "", candidate)
        candidate = re.sub(r"```\s*$", "", candidate).strip()

    start = candidate.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(candidate)):
        char = candidate[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                block = candidate[start : index + 1]
                try:
                    parsed = json.loads(block)
                except (TypeError, ValueError):
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def _clip(value: Optional[str], limit: int = _MAX_TEXT_LENGTH) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


def sanitize_entities(raw: Any) -> Dict[str, Any]:
    """Keep only allowlisted entity keys with simple, bounded values.

    Any attempt by the model to return identity/authorization data (a role,
    user id, permissions, ...) is dropped and logged as a security event: the
    model can never influence who the caller is.
    """
    if not isinstance(raw, dict):
        return {}

    violations = sorted(
        key for key in raw if str(key).lower() in FORBIDDEN_ENTITY_KEYS
    )
    if violations:
        # Key names only — never the values, which may contain user content.
        logger.warning(
            "SECURITY_EVENT model output contained identity/authorization keys: %s",
            violations,
        )

    clean: Dict[str, Any] = {}
    for key, value in raw.items():
        name = str(key).strip().lower()
        if name not in ENTITY_KEYS or value is None:
            continue
        if isinstance(value, bool) or isinstance(value, (int, float)):
            clean[name] = value
        elif isinstance(value, str):
            text = _clip(value, _MAX_ENTITY_VALUE_LENGTH)
            if text:
                clean[name] = text
        elif isinstance(value, dict):
            nested = {
                str(k): _clip(str(v), _MAX_ENTITY_VALUE_LENGTH)
                for k, v in value.items()
                if v is not None
            }
            nested = {k: v for k, v in nested.items() if v}
            if nested:
                clean[name] = nested
        elif isinstance(value, (list, tuple)):
            items = [
                _clip(str(v), _MAX_ENTITY_VALUE_LENGTH)
                for v in value
                if v is not None
            ]
            items = [v for v in items if v]
            if items:
                clean[name] = items
    return clean


def _sanitize_arguments(raw: Any) -> Dict[str, Any]:
    """Bound the shape of model-proposed tool arguments.

    Values are passed through untouched otherwise: the tool's Pydantic
    `input_schema` is the real validator (Section 09 pipeline).
    """
    if not isinstance(raw, dict):
        return {}
    clean: Dict[str, Any] = {}
    for key, value in raw.items():
        if len(clean) >= _MAX_ARGUMENT_KEYS:
            break
        name = str(key).strip()
        if not name or value is None:
            continue
        clean[name] = value
    return clean


def sanitize_tool_calls(raw: Any, *, max_calls: int) -> List[ProposedToolCall]:
    """Normalize requested tool calls; malformed entries are dropped.

    Names are NOT checked against the caller's role here. Whether a tool exists
    and whether the caller may run it is decided by the registry allowlist and
    the authorization engine, so a rejected call still produces an honest reply
    instead of a silently dropped action.
    """
    if not isinstance(raw, (list, tuple)):
        return []

    calls: List[ProposedToolCall] = []
    for item in raw:
        if len(calls) >= max_calls:
            logger.info("TOOL_REJECTED too many tool calls requested in one turn")
            break
        if isinstance(item, ProposedToolCall):
            name, arguments = item.name, item.arguments
        elif isinstance(item, dict):
            name = item.get("name") or item.get("tool")
            arguments = item.get("arguments")
            if arguments is None:
                arguments = item.get("parameters")
        else:
            name, arguments = getattr(item, "name", None), getattr(
                item, "arguments", None
            )

        if not isinstance(name, str) or not _TOOL_NAME_RE.match(name.strip()):
            logger.info("TOOL_REJECTED malformed tool name in model output")
            continue
        calls.append(
            ProposedToolCall(
                name=name.strip(), arguments=_sanitize_arguments(arguments)
            )
        )
    return calls


def _missing_information(raw: Any) -> List[str]:
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return []
    items = [_clip(str(v), 64) for v in raw if v is not None]
    return [v for v in items if v][:10]


def parse_decision(response: LLMResponse, *, max_tool_calls: int) -> ModelDecision:
    """Validate the model's first-pass output into a `ModelDecision`.

    Handles both native provider tool calls and the JSON decision block. Unknown
    intents fall back to `GENERAL_QUERY`; unknown entity keys are dropped.
    """
    payload = extract_json_object(response.text)
    has_payload = payload is not None
    payload = payload or {}

    decision = ModelDecision(
        intent=normalize_intent(payload.get("intent")),
        entities=sanitize_entities(payload.get("entities")),
        missing_information=_missing_information(payload.get("missing_information")),
        clarification_question=_clip(payload.get("clarification_question")),
        response_text=_clip(payload.get("response_text")),
    )

    # Native provider tool calls win; the JSON block is the fallback channel.
    if response.tool_calls:
        decision.tool_calls = sanitize_tool_calls(
            [
                {"name": call.name, "arguments": call.arguments}
                for call in response.tool_calls
            ],
            max_calls=max_tool_calls,
        )
    else:
        decision.tool_calls = sanitize_tool_calls(
            payload.get("tool_calls"), max_calls=max_tool_calls
        )

    # No JSON block at all: treat the whole text as a direct answer.
    if not has_payload and not decision.tool_calls:
        decision.response_text = _clip(response.text)

    return decision


def final_text(response: LLMResponse) -> Optional[str]:
    """Extract the user-facing text of the final pass.

    If the model still answers with a JSON decision block, its `response_text`
    is used so raw JSON is never shown to the user.
    """
    payload = extract_json_object(response.text)
    if payload is not None:
        return _clip(payload.get("response_text")) or _clip(
            payload.get("clarification_question")
        )
    return _clip(response.text)
