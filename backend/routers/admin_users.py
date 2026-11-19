from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models.ticket import Ticket
from ..models.user import (
    AdminUserResponse,
    User,
    UserRoleUpdate,
    UserStatusUpdate,
)
from ..services.auth_dependencies import AuthDependencies
from ..services.data_service import DataService

router: APIRouter = APIRouter(prefix="/admin/users", tags=["admin users"])


@router.get("", response_model=list[AdminUserResponse])
def get_users(
    request: Request,
    _admin: Annotated[User, Depends(AuthDependencies.require_admin)],
) -> list[AdminUserResponse]:
    """Return all user accounts with their limited administrative details."""
    users: list[User] = request.app.state.auth_service.get_users()
    return [_to_admin_response(user) for user in users]


@router.get("/{user_id}", response_model=AdminUserResponse)
def get_user(
    user_id: int,
    request: Request,
    _admin: Annotated[User, Depends(AuthDependencies.require_admin)],
) -> AdminUserResponse:
    """Return limited details for one account."""
    try:
        user: User = request.app.state.auth_service.get_user(user_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _to_admin_response(user)


@router.get("/{user_id}/tickets")
def get_user_tickets(
    user_id: int,
    request: Request,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
    _admin: Annotated[User, Depends(AuthDependencies.require_admin)],
) -> list[Ticket]:
    """Return tickets submitted by one account."""
    try:
        request.app.state.auth_service.get_user(user_id)
        return data_service.get_tickets_for_user(user_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch("/{user_id}/role", response_model=AdminUserResponse)
def update_user_role(
    user_id: int,
    changes: UserRoleUpdate,
    request: Request,
    _admin: Annotated[User, Depends(AuthDependencies.require_admin)],
) -> AdminUserResponse:
    """Change one account between regular user and administrator."""
    try:
        user: User = request.app.state.auth_service.update_user_role(
            user_id, changes.role
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _to_admin_response(user)


@router.patch("/{user_id}/status", response_model=AdminUserResponse)
def update_user_status(
    user_id: int,
    changes: UserStatusUpdate,
    request: Request,
    _admin: Annotated[User, Depends(AuthDependencies.require_admin)],
) -> AdminUserResponse:
    """Enable or disable one account."""
    try:
        user: User = request.app.state.auth_service.set_user_active(
            user_id, changes.is_active
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _to_admin_response(user)


def _to_admin_response(user: User) -> AdminUserResponse:
    """Convert an account model to the admin-only public representation."""
    return AdminUserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )
