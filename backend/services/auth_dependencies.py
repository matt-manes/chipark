from fastapi import HTTPException, Request

from ..models.user import User, UserRole
from .auth_service import AuthService


class AuthDependencies:
    """Provide reusable authentication dependencies for FastAPI routes."""

    @staticmethod
    def require_user(request: Request) -> User:
        """Resolve the current authenticated user.

        Parameters
        ----------
        request : Request
            Incoming HTTP request containing the bearer token.

        Returns
        -------
        User
            Authenticated account associated with the token.

        Raises
        ------
        HTTPException
            If the request has no valid bearer token.
        """
        auth_service: AuthService = request.app.state.auth_service
        user: User | None = auth_service.authenticate_authorization_header(
            request.headers.get("authorization")
        )
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Authentication is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    @staticmethod
    def require_admin(request: Request) -> User:
        """Resolve the current administrator.

        Parameters
        ----------
        request : Request
            Incoming HTTP request containing the bearer token.

        Returns
        -------
        User
            Authenticated administrator account.

        Raises
        ------
        HTTPException
            If the user is unauthenticated or lacks administrator privileges.
        """
        user: User = AuthDependencies.require_user(request)
        if user.role is not UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Administrator privileges are required.",
            )
        return user
