from typing import Annotated
from urllib.parse import SplitResult, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, Response

from ..models.user import (
    AuthenticatedUser,
    AuthenticatedUserResponse,
    LoginRequest,
    RegistrationRequest,
    User,
    UserResponse,
)
from ..services.auth_dependencies import AuthDependencies
from ..services.auth_errors import AuthenticationError

router: APIRouter = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=AuthenticatedUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    submission: RegistrationRequest,
    request: Request,
) -> AuthenticatedUserResponse:
    """Create an email/password account and return a bearer token."""
    try:
        authenticated_user: AuthenticatedUser = request.app.state.auth_service.register(
            submission.email, submission.password
        )
    except AuthenticationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return AuthenticatedUserResponse.from_authenticated_user(authenticated_user)


@router.post("/login", response_model=AuthenticatedUserResponse)
def login(
    submission: LoginRequest,
    request: Request,
) -> AuthenticatedUserResponse:
    """Authenticate an email/password account and return a bearer token."""
    try:
        authenticated_user: AuthenticatedUser = request.app.state.auth_service.login(
            submission.email, submission.password
        )
    except AuthenticationError as error:
        raise HTTPException(
            status_code=401,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    return AuthenticatedUserResponse.from_authenticated_user(authenticated_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    user: Annotated[User, Depends(AuthDependencies.require_user)],
) -> Response:
    """Revoke the current bearer token."""
    authorization: str = request.headers["authorization"]
    token: str = authorization.partition(" ")[2].strip()
    request.app.state.auth_service.logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def get_current_user(
    user: Annotated[User, Depends(AuthDependencies.require_user)],
) -> UserResponse:
    """Return the currently authenticated account."""
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )


@router.get("/google")
def begin_google_login(request: Request) -> RedirectResponse:
    """Redirect to Google to begin OpenID Connect login."""
    try:
        authorization_url: str = request.app.state.auth_service.begin_google_login()
    except AuthenticationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback")
async def finish_google_login(
    request: Request,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    oauth_error: Annotated[str | None, Query(alias="error")] = None,
) -> RedirectResponse:
    """Complete Google login and redirect with the bearer token in the URL fragment."""
    if oauth_error is not None:
        raise HTTPException(
            status_code=400, detail="Google sign-in was cancelled or denied."
        )
    if code is None or state is None:
        raise HTTPException(status_code=400, detail="Google callback is incomplete.")
    try:
        authenticated_user: AuthenticatedUser = (
            await request.app.state.auth_service.complete_google_login(code, state)
        )
    except AuthenticationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        frontend_url: str = request.app.state.auth_service.frontend_oauth_redirect_url()
    except AuthenticationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    parsed_url: SplitResult = urlsplit(frontend_url)
    fragment: str = urlencode(
        {
            "access_token": authenticated_user.access_token,
            "token_type": "Bearer",
            "expires_at": authenticated_user.expires_at.isoformat(),
        }
    )
    redirect_url: str = urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.query,
            fragment,
        )
    )
    return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)
