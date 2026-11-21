import argparse
import json
import re
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO, cast
from urllib.parse import SplitResult, urlsplit

from backend.tools.config import Config, ConfigError


@dataclass(frozen=True)
class ApiResponse:
    """Represent a captured HTTP response."""

    status: int
    body: str

    def json(self) -> object:
        """Decode the response body as JSON."""
        return json.loads(self.body)


class JsonValues:
    """Narrow decoded JSON containers to typed Python containers."""

    @staticmethod
    def as_object(value: object) -> dict[object, object] | None:
        """Return a JSON object when the value is a dictionary."""
        if not isinstance(value, dict):
            return None
        return cast(dict[object, object], value)

    @staticmethod
    def as_array(value: object) -> list[object] | None:
        """Return a JSON array when the value is a list."""
        if not isinstance(value, list):
            return None
        return cast(list[object], value)


class CurlRecorder:
    """Send HTTP requests with curl and record redacted transcripts."""

    REQUEST_TIMEOUT_SECONDS: int = 20
    STREAM_TIMEOUT_SECONDS: int = 3

    def __init__(self, base_url: str, output: TextIO) -> None:
        """Initialize the recorder and its sensitive values."""
        self._base_url: str = base_url.rstrip("/")
        self._output: TextIO = output
        self._secrets: set[str] = set()
        self.failures: int = 0

    def add_secret(self, value: str) -> None:
        """Add a value to redact from subsequent transcripts."""
        if value:
            self._secrets.add(value)

    def note(self, message: str) -> None:
        """Write a redacted note to the transcript."""
        self._output.write(f"\n{self._redact(message)}\n")
        self._output.flush()

    def request(
        self,
        label: str,
        method: str,
        path: str,
        expected: int | tuple[int, ...],
        token: str | None = None,
        payload: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
        stream: bool = False,
        retry_rate_limit: bool = True,
    ) -> ApiResponse:
        """Execute a request and record the actual response.

        Returns
        -------
        ApiResponse
            Status and unredacted body for use by subsequent requests.
        """
        config: list[str] = [
            f"url = {json.dumps(self._base_url + path)}",
            f"request = {json.dumps(method)}",
        ]
        if token is not None:
            config.append(f"header = {json.dumps('Authorization: Bearer ' + token)}")
        if payload is not None:
            config.append('header = "Content-Type: application/json"')
            config.append(f"data-binary = {json.dumps(json.dumps(payload))}")
        if headers is not None:
            for name, value in headers.items():
                config.append(f"header = {json.dumps(name + ': ' + value)}")
        timeout: int = (
            self.STREAM_TIMEOUT_SECONDS if stream else self.REQUEST_TIMEOUT_SECONDS
        )
        command: list[str] = [
            "curl",
            "--disable",
            "--include",
            "--suppress-connect-headers",
            "--silent",
            "--show-error",
            "--no-buffer",
            "--max-time",
            str(timeout),
            "--config",
            "-",
        ]
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            command,
            input="\n".join(config) + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        raw: str = completed.stdout
        status_match: re.Match[str] | None = re.search(r"(?m)^HTTP/\S+\s+(\d{3})", raw)
        status: int = int(status_match.group(1)) if status_match else 0
        body: str = raw.partition("\n\n")[2]
        self._remember_response_token(body)
        redacted: str = self._redact(raw)
        redacted = re.sub(r"(?im)^(set-cookie):[^\r\n]*", r"\1: [REDACTED]", redacted)
        if path.startswith("/auth/google"):
            redacted = re.sub(r"(?im)^(location):[^\r\n]*", r"\1: [REDACTED]", redacted)
        self.note(f"=== {label} ===\n{method} {self._base_url + path}")
        if payload is not None:
            self.note(f"Request JSON: {json.dumps(payload)}")
        self.note("Response (curl --include; secrets and OAuth redirects redacted):")
        self._output.write(redacted + "\n")
        if completed.stderr:
            self.note(f"curl stderr: {completed.stderr.strip()}")
        if status == 429 and retry_rate_limit:
            retry_match: re.Match[str] | None = re.search(
                r"(?im)^retry-after:\s*(\d+)\s*$", raw
            )
            retry_after: int = int(retry_match.group(1)) if retry_match else 0
            if 0 < retry_after <= 60:
                self.note(f"Rate limited; retrying after {retry_after} seconds.")
                time.sleep(retry_after)
                return self.request(
                    label,
                    method,
                    path,
                    expected,
                    token,
                    payload,
                    headers,
                    stream,
                    retry_rate_limit=False,
                )
        accepted_timeout: bool = stream and completed.returncode == 28 and status == 200
        expected_statuses: tuple[int, ...] = (
            (expected,) if isinstance(expected, int) else expected
        )
        if status not in expected_statuses or (
            completed.returncode != 0 and not accepted_timeout
        ):
            self.failures += 1
            self.note(
                f"UNEXPECTED: expected HTTP {expected}; received "
                f"{status or 'no HTTP response'}; curl exit {completed.returncode}."
            )
        elif accepted_timeout:
            self.note("Stream stopped after the configured capture timeout.")
        self._output.flush()
        return ApiResponse(status=status, body=body)

    def _remember_response_token(self, body: str) -> None:
        try:
            value: object = json.loads(body)
        except json.JSONDecodeError:
            return
        data: dict[object, object] | None = JsonValues.as_object(value)
        if data is not None:
            token: object = data.get("access_token")
            if isinstance(token, str):
                self.add_secret(token)

    def _redact(self, value: str) -> str:
        for secret in sorted(self._secrets, key=len, reverse=True):
            value = value.replace(json.dumps(secret)[1:-1], "[REDACTED]")
            value = value.replace(
                json.dumps(secret, ensure_ascii=False)[1:-1], "[REDACTED]"
            )
            value = value.replace(secret, "[REDACTED]")
        return value


class ApiEvidence:
    """Exercise the API against a disposable, isolated database."""

    def __init__(
        self, recorder: CurlRecorder, admin_email: str, admin_password: str
    ) -> None:
        """Initialize the run with configured administrator credentials."""
        self._recorder: CurlRecorder = recorder
        self._admin_email: str = admin_email
        self._admin_password: str = admin_password
        self._recorder.add_secret(admin_password)
        self._admin_token: str = ""
        self._password: str = secrets.token_urlsafe(24)
        self._recorder.add_secret(self._password)
        self._email: str = f"api-evidence-{secrets.token_hex(12)}@example.com"
        self._user_token: str = ""
        self._login_token: str = ""
        self._user_id: int = 0
        self._park_id: int = 0
        self._park_name: str = ""
        self._ticket_id: int = 0

    def run(self) -> None:
        """Run the evidence requests in dependency order."""
        self._public_routes()
        self._login_admin()
        self._register_and_login()
        self._account_routes()
        self._ticket_routes()
        self._admin_routes()
        self._notification_routes()
        self._finish()

    def _login_admin(self) -> None:
        response: ApiResponse = self._recorder.request(
            "Administrator login",
            "POST",
            "/auth/login",
            200,
            payload={"email": self._admin_email, "password": self._admin_password},
        )
        data: dict[object, object] | None = JsonValues.as_object(
            response.json() if response.status == 200 else None
        )
        token: object = data.get("access_token") if data is not None else None
        user: dict[object, object] | None = (
            JsonValues.as_object(data.get("user")) if data is not None else None
        )
        if not isinstance(token, str) or user is None or user.get("role") != "admin":
            raise RuntimeError(
                "Configured credentials did not authenticate an administrator."
            )
        self._admin_token = token

    def _public_routes(self) -> None:
        self._recorder.request("Health", "GET", "/", 200)
        parks: ApiResponse = self._recorder.request("List parks", "GET", "/parks", 200)
        data: list[object] | None = JsonValues.as_array(
            parks.json() if parks.status == 200 else None
        )
        if not data:
            raise RuntimeError("The isolated database must contain at least one park.")
        park: dict[object, object] | None = JsonValues.as_object(data[0])
        park_id: object = park.get("park_id") if park is not None else None
        park_name: object = park.get("name") if park is not None else None
        if not isinstance(park_id, int) or not isinstance(park_name, str):
            raise TypeError("The park response does not contain a usable ID and name.")
        self._park_id = park_id
        self._park_name = park_name
        self._recorder.request("Get park", "GET", f"/parks/{self._park_id}", 200)
        self._recorder.request(
            "Park conditions", "GET", f"/parks/{self._park_id}/conditions", 200
        )
        self._recorder.request("Invalid park ID", "GET", "/parks/not-an-id", 422)
        self._recorder.request("List tickets", "GET", "/tickets", 200)
        self._recorder.request(
            "Open tickets for park", "GET", f"/tickets/parks/{self._park_id}/open", 200
        )
        self._recorder.request("Begin Google login", "GET", "/auth/google", (302, 503))
        self._recorder.request(
            "Incomplete Google callback", "GET", "/auth/google/callback", 400
        )
        self._recorder.note(
            "Manual evidence required: complete the Google OAuth flow in a browser; "
            "the callback cannot be completed without the provider."
        )

    def _register_and_login(self) -> None:
        credentials: dict[str, object] = {
            "email": self._email,
            "password": self._password,
        }
        registration: ApiResponse = self._recorder.request(
            "Register synthetic account",
            "POST",
            "/auth/register",
            201,
            payload=credentials,
        )
        data: dict[object, object] | None = JsonValues.as_object(
            registration.json() if registration.status == 201 else None
        )
        token: object = data.get("access_token") if data is not None else None
        user: dict[object, object] | None = (
            JsonValues.as_object(data.get("user")) if data is not None else None
        )
        user_id: object = user.get("user_id") if user is not None else None
        if not isinstance(token, str) or not isinstance(user_id, int):
            raise TypeError("Registration did not return a usable account and token.")
        self._user_token = token
        self._user_id = user_id
        self._recorder.request(
            "Duplicate registration", "POST", "/auth/register", 409, payload=credentials
        )
        self._recorder.request(
            "Invalid login",
            "POST",
            "/auth/login",
            401,
            payload={"email": self._email, "password": "incorrect-password"},
        )
        login: ApiResponse = self._recorder.request(
            "Login", "POST", "/auth/login", 200, payload=credentials
        )
        login_data: dict[object, object] | None = JsonValues.as_object(
            login.json() if login.status == 200 else None
        )
        login_token: object = (
            login_data.get("access_token") if login_data is not None else None
        )
        if not isinstance(login_token, str):
            raise TypeError("Login did not return a usable token.")
        self._login_token = login_token

    def _account_routes(self) -> None:
        self._recorder.request("Anonymous profile", "GET", "/auth/me", 401)
        self._recorder.request("User profile", "GET", "/auth/me", 200, self._user_token)
        self._recorder.request(
            "Update synthetic profile",
            "PATCH",
            "/auth/me",
            200,
            self._user_token,
            {"email": f"updated-{self._email}"},
        )
        self._recorder.request(
            "Invalid profile update", "PATCH", "/auth/me", 400, self._user_token, {}
        )
        self._recorder.request(
            "My tickets", "GET", "/tickets/mine", 200, self._user_token
        )
        self._recorder.request(
            "Viewer denied admin access", "GET", "/admin/users", 403, self._user_token
        )

    def _ticket_routes(self) -> None:
        payload: dict[str, object] = {
            "park_name": self._park_name,
            "issue": "Disposable API evidence ticket",
            "estimated_hours": 1,
        }
        self._recorder.request(
            "Anonymous ticket submission", "POST", "/tickets", 401, payload=payload
        )
        created: ApiResponse = self._recorder.request(
            "Submit ticket", "POST", "/tickets", 201, self._user_token, payload
        )
        data: dict[object, object] | None = JsonValues.as_object(
            created.json() if created.status == 201 else None
        )
        ticket_id: object = data.get("ticket_id") if data is not None else None
        if not isinstance(ticket_id, int):
            raise TypeError("Ticket submission did not return a usable ticket ID.")
        self._ticket_id = ticket_id
        path: str = f"/tickets/{self._ticket_id}"
        self._recorder.request("Get ticket", "GET", path, 200)
        self._recorder.request(
            "Viewer denied ticket edit",
            "PATCH",
            path,
            403,
            self._user_token,
            {"issue": "Denied"},
        )
        self._recorder.request(
            "Viewer denied ticket close",
            "PATCH",
            f"{path}/close",
            403,
            self._user_token,
        )
        self._recorder.request(
            "Viewer denied ticket reopen",
            "PATCH",
            f"{path}/reopen",
            403,
            self._user_token,
        )
        self._recorder.request(
            "Viewer denied ticket deletion", "DELETE", path, 403, self._user_token
        )
        self._recorder.request(
            "Invalid ticket update", "PATCH", path, 422, self._admin_token, {}
        )
        self._recorder.request(
            "Update ticket",
            "PATCH",
            path,
            200,
            self._admin_token,
            {"issue": "Updated evidence ticket"},
        )
        self._recorder.request(
            "Close ticket", "PATCH", f"{path}/close", 200, self._admin_token
        )
        self._recorder.request(
            "Reopen ticket", "PATCH", f"{path}/reopen", 200, self._admin_token
        )

    def _admin_routes(self) -> None:
        path: str = f"/admin/users/{self._user_id}"
        self._recorder.request(
            "Viewer denied user list", "GET", "/admin/users", 403, self._user_token
        )
        self._recorder.request(
            "Viewer denied user details", "GET", path, 403, self._user_token
        )
        self._recorder.request(
            "Viewer denied user tickets",
            "GET",
            f"{path}/tickets",
            403,
            self._user_token,
        )
        self._recorder.request(
            "Viewer denied role change",
            "PATCH",
            f"{path}/role",
            403,
            self._user_token,
            {"role": "admin"},
        )
        self._recorder.request(
            "Viewer denied status change",
            "PATCH",
            f"{path}/status",
            403,
            self._user_token,
            {"is_active": False},
        )
        self._recorder.request(
            "List users", "GET", "/admin/users", 200, self._admin_token
        )
        self._recorder.request(
            "Get synthetic user", "GET", path, 200, self._admin_token
        )
        self._recorder.request(
            "Get user's tickets", "GET", f"{path}/tickets", 200, self._admin_token
        )
        self._recorder.request(
            "Set synthetic user role",
            "PATCH",
            f"{path}/role",
            200,
            self._admin_token,
            {"role": "user"},
        )
        self._recorder.request(
            "Set synthetic user status",
            "PATCH",
            f"{path}/status",
            200,
            self._admin_token,
            {"is_active": True},
        )

    def _notification_routes(self) -> None:
        response: ApiResponse = self._recorder.request(
            "List notifications", "GET", "/notifications", 200, self._user_token
        )
        notifications: list[object] | None = JsonValues.as_array(
            response.json() if response.status == 200 else None
        )
        if not notifications:
            raise RuntimeError("No notification was produced for the evidence ticket.")
        notification: dict[object, object] | None = JsonValues.as_object(
            notifications[0]
        )
        notification_id: object = (
            notification.get("notification_id") if notification is not None else None
        )
        if not isinstance(notification_id, int):
            raise TypeError("The notification response has no usable ID.")
        self._recorder.request(
            "Mark notification read",
            "PATCH",
            f"/notifications/{notification_id}/read",
            200,
            self._user_token,
        )
        self._recorder.request(
            "Missing notification",
            "PATCH",
            "/notifications/0/read",
            404,
            self._user_token,
        )
        self._recorder.request(
            "Invalid stream cursor",
            "GET",
            "/notifications/stream",
            400,
            self._user_token,
            headers={"Last-Event-ID": "-1"},
        )
        self._recorder.request(
            "Notification stream",
            "GET",
            "/notifications/stream",
            200,
            self._user_token,
            headers={"Last-Event-ID": "0"},
            stream=True,
        )

    def _finish(self) -> None:
        path: str = f"/tickets/{self._ticket_id}"
        self._recorder.request(
            "Delete evidence ticket", "DELETE", path, 204, self._admin_token
        )
        self._recorder.request("Deleted ticket", "GET", path, 404)
        self._recorder.request("Logout", "POST", "/auth/logout", 204, self._user_token)
        self._recorder.request(
            "Revoked token", "GET", "/auth/me", 401, self._user_token
        )
        self._recorder.request(
            "Revoke login token", "POST", "/auth/logout", 204, self._login_token
        )
        self._recorder.request(
            "Revoke administrator token", "POST", "/auth/logout", 204, self._admin_token
        )
        self._recorder.note(
            "The synthetic account and notifications remain in the database."
        )


def main() -> int:
    """Capture API evidence against an explicitly selected isolated environment.

    Returns
    -------
    int
        Zero if all checked responses match, otherwise nonzero.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Record redacted curl transcripts against an isolated ChiPark API."
    )
    parser.add_argument("--base-url", required=True, help="Isolated API origin")
    parser.add_argument(
        "--output", required=True, type=Path, help="New transcript file"
    )
    args: argparse.Namespace = parser.parse_args()
    base_url: str = args.base_url
    output_path: Path = args.output
    parsed: SplitResult = urlsplit(base_url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        parser.error("Provide an HTTP(S) origin without credentials or a path.")

    try:
        config: Config = Config()
        admin_email: str | None = config.CHIPARK_ADMIN_EMAIL
        admin_password: str | None = config.CHIPARK_ADMIN_PASSWORD
        if not admin_email or not admin_password:
            raise RuntimeError("Set CHIPARK_ADMIN_EMAIL and CHIPARK_ADMIN_PASSWORD.")
        with output_path.open("x", encoding="utf-8", newline="\n") as output:
            recorder: CurlRecorder = CurlRecorder(base_url, output)
            recorder.note(f"API evidence captured {datetime.now(UTC).isoformat()}")
            try:
                ApiEvidence(recorder, admin_email, admin_password).run()
            except (OSError, RuntimeError, json.JSONDecodeError) as error:
                recorder.note(f"Evidence capture failed: {error}")
                raise
            recorder.note(f"Unexpected responses: {recorder.failures}")
            return 1 if recorder.failures else 0
    except (
        OSError,
        RuntimeError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
        ConfigError,
    ) as error:
        print(f"Evidence capture failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
