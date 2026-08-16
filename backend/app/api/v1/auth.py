from fastapi import APIRouter, Depends

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_authenticated_user
from app.core.responses import ApiResponse, success_response

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=ApiResponse[AuthenticatedUser])
async def auth_me(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ApiResponse[AuthenticatedUser]:
    """Return the identity of the caller from the verified Firebase token."""
    return success_response(user)
