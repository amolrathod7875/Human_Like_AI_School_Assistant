from typing import Dict, Optional

# Canonical code -> display name + accepted aliases (case-insensitive).
_LANGUAGES: Dict[str, Dict[str, object]] = {
    "en": {"display": "English", "aliases": ["english", "en", "en-in", "eng"]},
    "hi": {"display": "Hindi", "aliases": ["hindi", "hi", "हिन्दी"]},
    "ta": {"display": "Tamil", "aliases": ["tamil", "ta"]},
    "te": {"display": "Telugu", "aliases": ["telugu", "te"]},
    "mr": {"display": "Marathi", "aliases": ["marathi", "mr"]},
    "bn": {"display": "Bengali", "aliases": ["bengali", "bangla", "bn"]},
    "gu": {"display": "Gujarati", "aliases": ["gujarati", "gu"]},
    "pa": {"display": "Punjabi", "aliases": ["punjabi", "pa"]},
    "kn": {"display": "Kannada", "aliases": ["kannada", "kn"]},
    "ml": {"display": "Malayalam", "aliases": ["malayalam", "ml"]},
    "ur": {"display": "Urdu", "aliases": ["urdu", "ur"]},
}

_FALLBACK_CODE = "en"

_ALIAS_MAP: Dict[str, str] = {}
for _code, _info in _LANGUAGES.items():
    _ALIAS_MAP[_code] = _code
    for _alias in _info["aliases"]:  # type: ignore[union-attr]
        _ALIAS_MAP[str(_alias).lower()] = _code


def normalize_language(language: Optional[str]) -> str:
    """Return the canonical language code. Unsupported input falls back to `en`."""
    if not language:
        return _FALLBACK_CODE
    key = language.strip().lower()
    return _ALIAS_MAP.get(key, _FALLBACK_CODE)


def get_language_instruction(language: Optional[str]) -> str:
    """Return a model instruction to respond in the (normalized) language.

    Unsupported languages safely fall back to English. This is a prompting
    instruction only and never affects authorization or security.
    """
    code = normalize_language(language)
    display = _LANGUAGES[code]["display"]  # type: ignore[index]
    return f"Respond in {display}."
