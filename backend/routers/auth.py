from typing import Annotated
from urllib.parse import SplitResult, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, Response

from ..models.user import (
    AuthenticatedUser,
    AuthenticatedUserResponse,
    LoginRequest,
    ProfileUpdateRequest,
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
    """Create an email/password account and issue a bearer token.

    Parameters
    ----------
    submission : RegistrationRequest
        Validated registration details.
    request : Request
        Incoming request containing the application authentication service.

    Returns
    -------
    AuthenticatedUserResponse
        Public account details and issued access token.

    Raises
    ------
    HTTPException
        If the email is already registered or registration details are invalid.
    """
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
    """Authenticate an account and issue a bearer token.

    Parameters
    ----------
    submission : LoginRequest
        Validated login credentials.
    request : Request
        Incoming request containing the application authentication service.

    Returns
    -------
    AuthenticatedUserResponse
        Public account details and issued access token.

    Raises
    ------
    HTTPException
        If the credentials are incorrect.
    """
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
    """Revoke the current bearer token.

    Parameters
    ----------
    request : Request
        Incoming request carrying the authenticated token.
    user : User
        Account authenticated by the dependency.

    Returns
    -------
    Response
        Empty response with status code 204.
    """
    authorization: str = request.headers["authorization"]
    token: str = authorization.partition(" ")[2].strip()
    request.app.state.auth_service.logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def get_current_user(
    user: Annotated[User, Depends(AuthDependencies.require_user)],
) -> UserResponse:
    """Return the currently authenticated account.

    Parameters
    ----------
    user : User
        Account authenticated by the dependency.

    Returns
    -------
    UserResponse
        Public details for the current account.
    """
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        password_login_enabled=user.password_login_enabled,
        google_login_enabled=user.google_login_enabled,
    )


@router.patch("/me", response_model=UserResponse)
def update_current_user(
    changes: ProfileUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(AuthDependencies.require_user)],
) -> UserResponse:
    """Update the authenticated account's email and/or password.

    Parameters
    ----------
    changes : ProfileUpdateRequest
        Requested profile fields.
    request : Request
        Incoming request containing the authentication service.
    user : User
        Authenticated account.

    Returns
    -------
    UserResponse
        Updated public account details.

    Raises
    ------
    HTTPException
        If the account type or supplied credentials do not allow the update.
    """
    try:
        updated_user: User = request.app.state.auth_service.update_profile(
            user.user_id,
            changes.email,
            changes.current_password,
            changes.new_password,
        )
    except AuthenticationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return UserResponse(
        user_id=updated_user.user_id,
        email=updated_user.email,
        role=updated_user.role,
        password_login_enabled=updated_user.password_login_enabled,
        google_login_enabled=updated_user.google_login_enabled,
    )


@router.get("/google")
def begin_google_login(request: Request) -> RedirectResponse:
    """Redirect the client to begin Google OpenID Connect login.

    Parameters
    ----------
    request : Request
        Incoming request containing the application authentication service.

    Returns
    -------
    RedirectResponse
        Redirect to Google's authorization endpoint.

    Raises
    ------
    HTTPException
        If Google OAuth configuration is incomplete.
    """
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
    """Complete Google login and redirect with the issued token.

    Parameters
    ----------
    request : Request
        Incoming callback request.
    code : str or None, default=None
        Authorization code returned by Google.
    state : str or None, default=None
        One-time state value from the authorization request.
    oauth_error : str or None, default=None
        OAuth error returned when Google rejects or cancels authorization.

    Returns
    -------
    RedirectResponse
        Redirect to the configured frontend with the token in its URL fragment.

    Raises
    ------
    HTTPException
        If callback parameters are invalid, authentication fails, or the frontend
        redirect URL is misconfigured.
    """
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
