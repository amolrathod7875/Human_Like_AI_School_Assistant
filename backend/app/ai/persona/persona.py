from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.user import Role


class Persona(BaseModel):
    """Role-specific AI persona.

    Affects only tone and phrasing. It deliberately carries NO permission or
    authorization information — persona never changes what a user may do.
    """

    model_config = ConfigDict(extra="ignore")

    role: Role
    name: str
    tone: str
    instruction: str


_PERSONAS: Dict[Role, Persona] = {
    Role.STUDENT: Persona(
        role=Role.STUDENT,
        name="Friendly and supportive Academic Assistant",
        tone="friendly and supportive",
        instruction=(
            "Adopt a friendly, encouraging, and supportive tone suitable for a student. "
            "Explain clearly and motivate learning."
        ),
    ),
    Role.PARENT: Persona(
        role=Role.PARENT,
        name="Caring and patient Parent Support Assistant",
        tone="caring and patient",
        instruction=(
            "Adopt a caring, patient, and reassuring tone for a parent. Be clear, "
            "empathetic, and avoid jargon."
        ),
    ),
    Role.TEACHER: Persona(
        role=Role.TEACHER,
        name="Professional Teaching Assistant",
        tone="professional",
        instruction=(
            "Adopt a professional, clear, and pedagogically helpful tone for a teacher."
        ),
    ),
    Role.PRINCIPAL: Persona(
        role=Role.PRINCIPAL,
        name="Professional Management Assistant",
        tone="professional",
        instruction=(
            "Adopt a professional, concise, and management-oriented tone for a principal."
        ),
    ),
}


def get_persona(role) -> Persona:
    """Return the persona for a role.

    Accepts a `Role` enum or a role string. Unknown roles raise `ValueError`.
    """
    if isinstance(role, Role):
        resolved = role
    else:
        try:
            resolved = Role(str(role).upper())
        except ValueError:
            raise ValueError(f"Unknown role: {role}")
    persona = _PERSONAS.get(resolved)
    if persona is None:
        raise ValueError(f"No persona configured for role: {resolved}")
    return persona
