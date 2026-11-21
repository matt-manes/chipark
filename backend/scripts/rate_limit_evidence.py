import argparse
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, TextIO
from urllib.parse import SplitResult, urlsplit

from backend.scripts.api_evidence import ApiResponse, CurlRecorder
from backend.tools.config import Config
from backend.tools.rate_limiting import RateLimitPolicy


class RateLimitEvidence:
    """Capture authentication and global rate-limit responses."""

    def __init__(
        self,
        recorder: CurlRecorder,
        auth_policy: RateLimitPolicy,
        global_policy: RateLimitPolicy,
        park_id: int,
    ) -> None:
        self._recorder: CurlRecorder = recorder
        self._auth_policy: RateLimitPolicy = auth_policy
        self._global_policy: RateLimitPolicy = global_policy
        self._park_id: int = park_id

    def run(self) -> None:
        """Capture a 429 for each endpoint without waiting between requests."""
        self._recorder.note(
            "Authentication requests also consume the global allowance; "
            "a 429 on this endpoint may be caused by either limit. "
            "These requests also count toward the subsequent park test."
        )
        self._request_until_limited(
            "Authentication",
            "POST",
            "/auth/login",
            self._auth_policy,
            422,
            payload={},
        )
        self._request_until_limited(
            "Park",
            "GET",
            f"/parks/{self._park_id}",
            self._global_policy,
            200,
            cache_bust=True,
        )

    def _request_until_limited(
        self,
        label: str,
        method: str,
        path: str,
        policy: RateLimitPolicy,
        allowed_status: int,
        payload: dict[str, object] | None = None,
        cache_bust: bool = False,
    ) -> None:
        expected: tuple[int, int] = (allowed_status, 429)
        for attempt in range(1, policy.max_requests + 2):
            previous_failures: int = self._recorder.failures
            request_path: str = (
                f"{path}?rate_limit_evidence={secrets.token_hex(16)}"
                if cache_bust
                else path
            )
            response: ApiResponse = self._recorder.request(
                f"{label} request {attempt}",
                method,
                request_path,
                expected,
                payload=payload,
                retry_rate_limit=False,
            )
            if (
                self._recorder.failures != previous_failures
                or response.status not in expected
            ):
                raise RuntimeError(f"{label} request {attempt} failed.")
            if response.status == 429:
                self._recorder.note(
                    f"{label} endpoint returned 429 on request {attempt}."
                )
                return
        raise RuntimeError(
            f"{label} endpoint did not return 429 within "
            f"{policy.max_requests + 1} requests; check the server's settings "
            "and whether the requests fit within its rate-limit window."
        )


class RateLimitEvidenceCommand:
    """Parse arguments and run the rate-limit evidence capture."""

    DEFAULT_PARK_ID: ClassVar[int] = 1

    @staticmethod
    def _origin(value: str) -> str:
        parsed: SplitResult = urlsplit(value)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise argparse.ArgumentTypeError(
                "Provide an HTTP(S) origin without credentials or a path."
            )
        return value

    @staticmethod
    def _park_id(value: str) -> int:
        try:
            park_id: int = int(value)
        except ValueError as error:
            raise argparse.ArgumentTypeError(
                "Park ID must be a positive integer."
            ) from error
        if park_id <= 0:
            raise argparse.ArgumentTypeError("Park ID must be a positive integer.")
        return park_id

    @staticmethod
    def main() -> int:
        """Capture rate-limit evidence against the selected API."""
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Record curl responses demonstrating API rate limits."
        )
        parser.add_argument(
            "--base-url", required=True, type=RateLimitEvidenceCommand._origin
        )
        parser.add_argument(
            "--output", required=True, type=Path, help="New transcript file"
        )
        parser.add_argument(
            "--park-id",
            type=RateLimitEvidenceCommand._park_id,
            default=RateLimitEvidenceCommand.DEFAULT_PARK_ID,
            help=(
                f"ID of an existing park (default: "
                f"{RateLimitEvidenceCommand.DEFAULT_PARK_ID})"
            ),
        )
        args: argparse.Namespace = parser.parse_args()
        base_url: str = args.base_url
        output_path: Path = args.output
        park_id: int = args.park_id

        try:
            config: Config = Config()
            auth_policy: RateLimitPolicy = RateLimitPolicy.from_value(
                config.CHIPARK_RATE_LIMIT_AUTH
            )
            global_policy: RateLimitPolicy = RateLimitPolicy.from_value(
                config.CHIPARK_RATE_LIMIT_GLOBAL
            )
            with output_path.open("x", encoding="utf-8", newline="\n") as output:
                return RateLimitEvidenceCommand._capture(
                    base_url, output, auth_policy, global_policy, park_id
                )
        except (OSError, RuntimeError, ValueError) as error:
            print(f"Rate-limit evidence capture failed: {error}", file=sys.stderr)
            return 1

    @staticmethod
    def _capture(
        base_url: str,
        output: TextIO,
        auth_policy: RateLimitPolicy,
        global_policy: RateLimitPolicy,
        park_id: int,
    ) -> int:
        recorder: CurlRecorder = CurlRecorder(base_url, output)
        recorder.note(f"Rate-limit evidence captured {datetime.now(UTC).isoformat()}")
        recorder.note(
            f"Configured auth limit: {auth_policy.max_requests} requests per "
            f"{auth_policy.window_seconds} seconds; global limit: "
            f"{global_policy.max_requests} requests per "
            f"{global_policy.window_seconds} seconds."
        )
        try:
            RateLimitEvidence(recorder, auth_policy, global_policy, park_id).run()
        except (OSError, RuntimeError) as error:
            recorder.note(f"Evidence capture failed: {error}")
            raise
        return 0


if __name__ == "__main__":
    sys.exit(RateLimitEvidenceCommand.main())
