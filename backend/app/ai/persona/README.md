# Section 08 — Persona + Language Manager

Role-specific AI persona configuration and language selection. This module only
affects **tone and phrasing**; it never affects permissions or security.

## Personas (`app.ai.persona.persona`)

`get_persona(role) -> Persona` maps each role to a persona:

| Role | Persona |
| --- | --- |
| STUDENT | Friendly and supportive Academic Assistant |
| PARENT | Caring and patient Parent Support Assistant |
| TEACHER | Professional Teaching Assistant |
| PRINCIPAL | Professional Management Assistant |

`Persona` carries only `role`, `name`, `tone`, and `instruction` — **no
permission/authorization fields**. Persona therefore cannot change what a user
is allowed to do (that is the authorization engine's job).

## Language (`app.ai.persona.language`)

Supported languages: English, Hindi, Tamil, Telugu, Marathi, Bengali,
Gujarati, Punjabi, Kannada, Malayalam, Urdu.

- `normalize_language(language) -> str` — returns the canonical language code
  (e.g. `"hi"`). Unknown/empty input safely falls back to `"en"`.
- `get_language_instruction(language) -> str` — returns a prompting instruction
  like `"Respond in Hindi."`. Unsupported input falls back to English.

Language selection is a prompting hint only; it cannot bypass security and the
orchestrator is responsible for persisting the chosen language on the
conversation.

## Usage

```python
from app.ai import get_persona, normalize_language, get_language_instruction

persona = get_persona(role)                       # Role or role string
instruction = get_language_instruction("hi")       # "Respond in Hindi."
code = normalize_language("Hindi")                # "hi"
```

## Tests
`tests/test_persona_language.py` covers: all roles map to expected personas,
string roles, unknown role rejection, normalization of every supported language
(name + code variants), unsupported/empty language fallback to English, language
instructions (with fallback), and that personas contain no permission fields.
