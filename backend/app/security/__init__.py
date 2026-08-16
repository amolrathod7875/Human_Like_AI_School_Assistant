import logging
import re
from typing import List, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger("app.security")

# Canonical log markers required by Section 12.
SECURITY_EVENT = "SECURITY_EVENT"
AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
TOOL_REJECTED = "TOOL_REJECTED"
SUSPICIOUS_INPUT = "SUSPICIOUS_INPUT"


def log_security_event(
    marker: str,
    message: str,
    *,
    severity: str = "warning",
) -> None:
    """Emit a security log line with a canonical marker.

    Never include secrets, tokens, keys, or private keys in `message` — the
    caller is responsible for passing only safe, non-sensitive detail.
    """
    line = f"{marker} {message}"
    level = getattr(logging, severity.upper(), logging.WARNING)
    logger.log(level, line)


# ----------------------------------------------------------------- suspicion
# Patterns that strongly suggest a prompt-injection / extraction attempt. These
# are heuristic and additive: a match only raises an alert and (where relevant)
# strengthens guardrail instructions. They never, by themselves, change what a
# user is authorized to do.
_INJECTION_PATTERNS: List[Tuple[str, str]] = [
    (r"ignore (all |any |previous |prior |upar ke |pichle )?instructions?", "ignore_instructions"),
    (r"disregard (the|your) (above|previous|prior) (instructions|prompt)", "ignore_instructions"),
    (r"forget (everything|all|your) (previous|prior|above)", "forget_prompt"),
    (r"(reveal|tell me|show|dump|print|give me|batao|dikhao).{0,25}(system prompt|your (prompt|instructions)|initial (prompt|instructions)|सिस्टम प्रॉम्प्ट|सिस्टम प्रॉम्प्ट|system प्रॉम्प्ट)", "system_prompt_extraction"),
    (r"(system prompt|initial (prompt|instructions)|developer (message|instructions)|सिस्टम प्रॉम्प्ट)", "system_prompt_extraction"),
    (r"(jailbreak|dan mode|developer mode|do anything now|kuch bhi karo)", "jailbreak"),
    (r"(you are now|pretend to be|act as|i am the|i'm the|main hoon|मैं हूँ).{0,40}(principal|admin|administrator|teacher|parent|manager|owner|प्रिंसिपल|प्रधानाध्यापक)", "role_claim"),
    (r"\bprincipal\b", "role_claim"),
    (r"(reveal|give me|show|tell me|send|expose|leak|dikhao).{0,25}(secret|api[_ ]?key|private[_ ]?key|password|token|credential)", "credential_extraction"),
    (r"(exfiltrate|send to|post to|fetch from|make an http|bahar bhejo)", "exfiltration"),
    (r"(run|execute|call).{0,20}(shell|code|command|script)", "code_execution"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE | re.UNICODE), name) for p, name in _INJECTION_PATTERNS]


def detect_suspicious_input(text: Optional[str]) -> Optional[str]:
    """Return a short reason string if `text` looks like an injection attempt.

    Detection is language-agnostic enough to catch transliterated attacks
    (e.g. "system prompt" typed in Devanagari is still matched). It never blocks
    the request: the orchestrator still applies the authoritative authorization
    and tool allowlist, so a flagged message is handled like any other.
    """
    if not text or not isinstance(text, str):
        return None
    # Normalize whitespace so "ignore   previous instructions" still matches.
    normalized = re.sub(r"\s+", " ", text)
    for pattern, name in _COMPILED:
        if pattern.search(normalized):
            return name
    return None


# ------------------------------------------------------------------ secrets
# Redaction applied to MODEL output before it is ever fed back into the next
# generation context or persisted as a result, so a model that echoes a secret
# cannot launder it into a later turn. (Do not sanitize user input: that is the
# caller's own data and must be preserved verbatim.)
_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)(secret|token|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(firebase[_-]?private[_-]?key)\s*[:=].{8,}"),
    re.compile(r"(?i)sk-[A-Za-z0-9]{20,}"),
]


def redact_secrets(text: Optional[str]) -> Optional[str]:
    """Replace obvious secret shapes with a placeholder.

    Returns the text unchanged in type (None stays None) but with any matched
    secret redacted. Applied only to model-produced content.
    """
    if not text or not isinstance(text, str):
        return text
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def sanitize_model_output(value: Optional[str]) -> Optional[str]:
    """Strip secrets from model output before it reaches context storage."""
    return redact_secrets(value)


def sanitize_tool_arguments(arguments: dict) -> dict:
    """Redact secrets found inside model-proposed tool arguments (recursively).

    The tool's Pydantic `input_schema` remains the real validator; this is a
    defense-in-depth cleanup so a leaked secret in an argument cannot be echoed
    back through a tool result.
    """
    if not isinstance(arguments, dict):
        return arguments

    cleaned: dict = {}
    for key, val in arguments.items():
        if isinstance(val, str):
            cleaned[key] = redact_secrets(val)
        elif isinstance(val, dict):
            cleaned[key] = sanitize_tool_arguments(val)
        elif isinstance(val, list):
            cleaned[key] = [
                sanitize_tool_arguments(v) if isinstance(v, dict) else
                (redact_secrets(v) if isinstance(v, str) else v)
                for v in val
            ]
        else:
            cleaned[key] = val
    return cleaned
