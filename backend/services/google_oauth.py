import base64
import hashlib
import json
import os
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from .auth_errors import AuthenticationError


@dataclass(frozen=True)
class GoogleIdentity:
    """Represent a Google account verified through OpenID Connect."""

    email: str
    subject: str


class GoogleOAuthClient:
    """Handle Google authorization-code and PKCE exchanges."""

    _AUTHORIZATION_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    _TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    _USERINFO_URL: str = "https://openidconnect.googleapis.com/v1/userinfo"

    def authorization_url(self, state: str, code_verifier: str) -> str:
        """Create a Google authorization URL for a PKCE-protected login."""
        self._required_environment("CHIPARK_GOOGLE_CLIENT_SECRET")
        query: str = urlencode(
            {
                "client_id": self._required_environment("CHIPARK_GOOGLE_CLIENT_ID"),
                "redirect_uri": self._required_environment(
                    "CHIPARK_GOOGLE_REDIRECT_URI"
                ),
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "code_challenge": self._code_challenge(code_verifier),
                "code_challenge_method": "S256",
            }
        )
        return f"{self._AUTHORIZATION_URL}?{query}"

    async def get_verified_identity(
        self, authorization_code: str, code_verifier: str
    ) -> GoogleIdentity:
        """Exchange an authorization code and retrieve its verified Google identity."""
        client_id: str = self._required_environment("CHIPARK_GOOGLE_CLIENT_ID")
        client_secret: str = self._required_environment("CHIPARK_GOOGLE_CLIENT_SECRET")
        redirect_uri: str = self._required_environment("CHIPARK_GOOGLE_REDIRECT_URI")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                token_response: httpx.Response = await client.post(
                    self._TOKEN_URL,
                    data={
                        "code": authorization_code,
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                        "code_verifier": code_verifier,
                    },
                )
                token_response.raise_for_status()
                token_payload: object = token_response.json()
                access_token: str = self._read_string(token_payload, "access_token")
                userinfo_response: httpx.Response = await client.get(
                    self._USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                userinfo_response.raise_for_status()
                userinfo: object = userinfo_response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as error:
            raise AuthenticationError(
                "Google authentication could not be completed."
            ) from error

        if (
            not isinstance(userinfo, dict)
            or "email_verified" not in userinfo
            or not userinfo["email_verified"]
        ):
            raise AuthenticationError("Google did not verify the account email.")
        return GoogleIdentity(
            email=self._read_string(userinfo, "email"),  # type: ignore
            subject=self._read_string(userinfo, "sub"),  # type: ignore
        )

    @staticmethod
    def _code_challenge(code_verifier: str) -> str:
        """Create the URL-safe SHA-256 PKCE challenge."""
        digest: bytes = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    @staticmethod
    def _required_environment(name: str) -> str:
        """Return a required OAuth environment setting."""
        value: str | None = os.environ.get(name)
        if value is None or not value.strip():
            raise AuthenticationError(f"Set {name} to enable Google sign-in.")
        return value.strip()

    @staticmethod
    def _read_string(payload: object, key: str) -> str:
        """Read a non-empty string field from a JSON response."""
        if not isinstance(payload, dict):
            raise AuthenticationError("Google returned an invalid response.")
        value: object = payload.get(key)  # type: ignore
        if not isinstance(value, str) or not value:
            raise AuthenticationError("Google returned an invalid response.")
        return value
