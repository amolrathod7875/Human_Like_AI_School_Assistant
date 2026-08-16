from fastapi import APIRouter, Depends

from app.ai.orchestrator.orchestrator import handle_message
from app.ai.orchestrator.schemas import ChatRequest, ChatResponse
from app.auth.authorization.context import (
    AuthorizationContext,
    get_authorization_context,
)
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_authenticated_user
from app.core.responses import ApiResponse, success_response

router = APIRouter(prefix="/ai", tags=["ai"])


async def get_auth_context(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> AuthorizationContext:
    """Resolve the caller's authorization context from the verified token.

    Role/active/relationship come strictly from the stored Firestore profile —
    never from the request body, and never from the model.
    """
    return get_authorization_context(user)


@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat(
    payload: ChatRequest,
    context: AuthorizationContext = Depends(get_auth_context),
) -> ApiResponse[ChatResponse]:
    """Primary natural-language endpoint (orchestrator entry point)."""
    return success_response(await handle_message(context, payload))
