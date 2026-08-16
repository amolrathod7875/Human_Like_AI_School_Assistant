from fastapi import APIRouter, Depends

from app.ai.orchestrator.orchestrator import handle_message
from app.ai.orchestrator.schemas import ChatRequest
from app.auth.authorization.context import (
    AuthorizationContext,
    get_authorization_context,
)
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_authenticated_user
from app.core.responses import ApiResponse, success_response
from app.schemas.avatar import (
    AudioMetadata,
    AvatarContractResponse,
)
from app.services.avatar_service import (
    build_avatar_contract,
    get_avatar_contract_spec,
)

router = APIRouter(prefix="/avatar", tags=["avatar"])


async def get_auth_context(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> AuthorizationContext:
    """Resolve the caller's authorization context from the verified token.

    Role/active/relationship come strictly from the stored Firestore profile —
    never from the request body, and never from the model.
    """
    return get_authorization_context(user)


@router.get("/contract", response_model=ApiResponse[dict])
async def avatar_contract_spec() -> ApiResponse[dict]:
    """Expose the avatar contract specification (states, emotions, example).

    Static, non-sensitive metadata so the frontend can discover the exact enum
    values and response shape without a live turn.
    """
    return success_response(get_avatar_contract_spec())


@router.post("/contract", response_model=ApiResponse[AvatarContractResponse])
async def avatar_contract(
    payload: ChatRequest,
    context: AuthorizationContext = Depends(get_auth_context),
) -> ApiResponse[AvatarContractResponse]:
    """Run a turn and return the canonical avatar contract for Lovable.

    Identity/role are resolved from the verified token, never the body. The
    response carries everything the frontend needs to render avatar state,
    emotion, and (when available) audio — no separate avatar provider required.
    """
    chat = await handle_message(context, payload)
    return success_response(build_avatar_contract(chat))
