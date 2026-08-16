import pytest

from app.ai.persona import get_language_instruction, get_persona, normalize_language
from app.ai.persona.persona import Persona
from app.schemas.user import Role


def test_all_roles_map_to_expected_personas():
    expected = {
        Role.STUDENT: "Friendly and supportive Academic Assistant",
        Role.PARENT: "Caring and patient Parent Support Assistant",
        Role.TEACHER: "Professional Teaching Assistant",
        Role.PRINCIPAL: "Professional Management Assistant",
    }
    for role, name in expected.items():
        persona = get_persona(role)
        assert persona.name == name
        assert persona.tone
        assert persona.instruction


def test_get_persona_accepts_string_role():
    assert get_persona("parent").name == "Caring and patient Parent Support Assistant"
    assert get_persona("PRINCIPAL").name == "Professional Management Assistant"


def test_unknown_role_raises():
    with pytest.raises(ValueError):
        get_persona("SUPERADMIN")


def test_language_normalization():
    # English variants
    assert normalize_language("English") == "en"
    assert normalize_language("english") == "en"
    assert normalize_language("en") == "en"
    assert normalize_language("en-IN") == "en"
    # Each supported language (name + code)
    assert normalize_language("Hindi") == "hi"
    assert normalize_language("hi") == "hi"
    assert normalize_language("Tamil") == "ta"
    assert normalize_language("Telugu") == "te"
    assert normalize_language("Marathi") == "mr"
    assert normalize_language("Bengali") == "bn"
    assert normalize_language("Gujarati") == "gu"
    assert normalize_language("Punjabi") == "pa"
    assert normalize_language("Kannada") == "kn"
    assert normalize_language("Malayalam") == "ml"
    assert normalize_language("Urdu") == "ur"


def test_unsupported_language_falls_back_to_english():
    assert normalize_language("Klingon") == "en"
    assert normalize_language("fr") == "en"
    assert normalize_language(None) == "en"
    assert normalize_language("") == "en"
    assert normalize_language("   ") == "en"


def test_language_instruction_and_fallback():
    assert get_language_instruction("hi") == "Respond in Hindi."
    assert get_language_instruction("Tamil") == "Respond in Tamil."
    # Unsupported -> safe English fallback
    assert get_language_instruction("fr") == "Respond in English."
    assert get_language_instruction(None) == "Respond in English."


def test_persona_cannot_change_permissions():
    fields = set(Persona.model_fields.keys())
    assert fields == {"role", "name", "tone", "instruction"}
    # No permission-like fields anywhere in the persona.
    assert not any("perm" in f or f.startswith("can_") for f in fields)
    for role in Role:
        dumped = get_persona(role).model_dump()
        assert "permission" not in dumped
        assert "can_" not in " ".join(dumped.keys())
