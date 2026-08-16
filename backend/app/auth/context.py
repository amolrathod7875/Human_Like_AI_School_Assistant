from typing import Optional

from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """Identity extracted from a verified Firebase ID token.

    This carries only the authenticated subject, not any application role.
    Authorization/roles are owned by later sections (e.g. Section 03).
    """

    firebase_uid: str
    email: Optional[str] = None
    name: Optional[str] = None
