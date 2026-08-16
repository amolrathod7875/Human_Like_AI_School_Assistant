from typing import Optional, Protocol, runtime_checkable
from uuid import uuid4

from app.auth.authorization.context import AuthorizationContext
from app.schemas.user import Role
from app.core.errors import AppError
from app.repositories import SupportRequestRepository
from app.schemas.collections import SupportRequest


# Status vocabulary for escalation requests (Section 13 contract).
STATUS_PENDING = "PENDING"
STATUS_CONFIRMED = "CONFIRMED"
STATUS_FAILED = "FAILED"
STATUS_CANCELLED = "CANCELLED"


@runtime_checkable
class HumanSupportAdapter(Protocol):
    """Adapter for the (mock) external human-support backend.

    Kept behind an interface so a real provider can be swapped in later without
    touching the service. The mock never contacts a paid third party.
    """

    async def submit(self, request: SupportRequest) -> str:
        """Return a final status: one of CONFIRMED / FAILED."""
        ...


class MockHumanSupportAdapter:
    """Deterministic stand-in for the human-support backend.

    Returns `CONFIRMED` by default; tests inject a callable to force `FAILED`
    or other behavior. The contract is intentionally tiny: the backend confirms
    or fails the hand-off, and the status is what the AI is allowed to relay.
    """

    def __init__(self, outcome: Optional[str] = None) -> None:
        self._outcome = outcome or STATUS_CONFIRMED
        self.submitted: list[SupportRequest] = []

    async def submit(self, request: SupportRequest) -> str:
        self.submitted.append(request)
        if callable(self._outcome):
            return self._outcome(request)
        return self._outcome


# Module-level adapter (tests override via set_human_support_adapter).
_adapter: Optional[HumanSupportAdapter] = None


def set_human_support_adapter(adapter: Optional[HumanSupportAdapter]) -> None:
    global _adapter
    _adapter = adapter


def get_human_support_adapter() -> HumanSupportAdapter:
    global _adapter
    if _adapter is None:
        _adapter = MockHumanSupportAdapter()
    return _adapter



# Dependency injection point (overridden by tests).
_support_repo: Optional[SupportRequestRepository] = None


def set_support_repository(repo: Optional[SupportRequestRepository]) -> None:
    global _support_repo
    _support_repo = repo


def get_support_repository() -> SupportRequestRepository:
    global _support_repo
    if _support_repo is None:
        _support_repo = SupportRequestRepository()
    return _support_repo


def _repo() -> SupportRequestRepository:
    return SupportRequestRepository()


def _new_id() -> str:
    return f"req_{uuid4().hex[:12]}"


async def request_teacher_contact(
    context: AuthorizationContext,
    student_id: str,
    reason: str,
) -> SupportRequest:
    """Create (and dispatch) a parent/teacher → teacher contact request.

    The caller's role/authorization is enforced by the route/tool before this is
    called (Section 05 policies). Outcome is decided by the human-support adapter.
    """
    from app.auth.authorization.policies import can_create_teacher_escalation

    outcome = can_create_teacher_escalation(context, student_id)
    if not outcome.allowed:
        raise AppError(outcome.message or "Forbidden", "FORBIDDEN", status_code=403)

    request = SupportRequest(
        id="",
        user_id=context.user_id,
        requested_by=context.user_id,
        requester_role=context.role.value,
        target_type="TEACHER",
        target_id=None,  # resolved by the support backend against the child's class
        student_id=student_id,
        reason=reason,
        status=STATUS_PENDING,
    )
    return await _dispatch(request)


async def request_management_contact(
    context: AuthorizationContext,
    reason: str,
    student_id: Optional[str] = None,
) -> SupportRequest:
    """Create (and dispatch) a teacher/principal → management contact request."""
    from app.auth.authorization.policies import can_create_management_escalation

    outcome = can_create_management_escalation(context)
    if not outcome.allowed:
        raise AppError(outcome.message or "Forbidden", "FORBIDDEN", status_code=403)

    request = SupportRequest(
        id="",
        user_id=context.user_id,
        requested_by=context.user_id,
        requester_role=context.role.value,
        target_type="MANAGEMENT",
        target_id=None,
        student_id=student_id,
        reason=reason,
        status=STATUS_PENDING,
    )
    return await _dispatch(request)


async def _dispatch(request: SupportRequest) -> SupportRequest:
    """Persist the request, ask the adapter for a verdict, and store the result.

    The persisted status is the single source of truth the AI may relay: only a
    `CONFIRMED` status justifies saying a human was contacted.
    """
    repo = get_support_repository()
    created = repo.create(request.model_copy(update={"id": _new_id()}))
    try:
        status = await get_human_support_adapter().submit(created)
    except Exception:
        status = STATUS_FAILED
    if status not in (STATUS_CONFIRMED, STATUS_FAILED, STATUS_CANCELLED):
        status = STATUS_FAILED
    updated = repo.update(created.id, {"status": status})
    return updated


async def get_request(request_id: str, context: AuthorizationContext) -> SupportRequest:
    """Fetch a support request by id.

    Ownership: the requester, or any principal (school-wide), may read it.
    """
    repo = get_support_repository()
    found = repo.get(request_id)
    if found is None:
        raise AppError("Support request not found", "NOT_FOUND", status_code=404)
    if context.role == Role.PRINCIPAL or found.user_id == context.user_id:
        return found
    raise AppError("Not authorized for this request", "FORBIDDEN", status_code=403)
