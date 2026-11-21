import io
import subprocess

import pytest

from backend.scripts.api_evidence import CurlRecorder
from backend.scripts.rate_limit_evidence import RateLimitEvidence
from backend.tools.rate_limiting import RateLimitPolicy


class CurlResponses:
    def __init__(self, statuses: list[int]) -> None:
        self.statuses: list[int] = statuses
        self.configs: list[str] = []

    def run(self, *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        config: object = kwargs.get("input")
        assert isinstance(config, str)
        self.configs.append(config)
        status: int = self.statuses.pop(0)
        headers: str = "Retry-After: 60\n" if status == 429 else ""
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=f"HTTP/1.1 {status} Response\n{headers}\n{{}}",
            stderr="",
        )


@pytest.fixture
def successful_capture(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[CurlResponses, str]:
    curl: CurlResponses = CurlResponses([422, 429, 200, 429])
    monkeypatch.setattr(subprocess, "run", curl.run)
    output: io.StringIO = io.StringIO()
    recorder: CurlRecorder = CurlRecorder("http://localhost:8000", output)
    evidence: RateLimitEvidence = RateLimitEvidence(
        recorder, RateLimitPolicy(2, 60), RateLimitPolicy(3, 60), 1
    )

    evidence.run()

    return curl, output.getvalue()


def test_capture_requests_auth_before_park(
    successful_capture: tuple[CurlResponses, str],
) -> None:
    curl: CurlResponses = successful_capture[0]
    assert len(curl.configs) == 4
    assert all("/auth/login" in config for config in curl.configs[:2])
    assert all("/parks/1?" in config for config in curl.configs[2:])


def test_capture_records_each_response(
    successful_capture: tuple[CurlResponses, str],
) -> None:
    assert successful_capture[1].count("HTTP/1.1") == 4


def test_park_requests_have_distinct_cache_keys(
    successful_capture: tuple[CurlResponses, str],
) -> None:
    assert successful_capture[0].configs[2] != successful_capture[0].configs[3]


def test_capture_records_that_auth_requests_count_toward_global_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    curl: CurlResponses = CurlResponses([429, 429])
    monkeypatch.setattr(subprocess, "run", curl.run)
    output: io.StringIO = io.StringIO()
    recorder: CurlRecorder = CurlRecorder("http://localhost:8000", output)

    RateLimitEvidence(recorder, RateLimitPolicy(1, 60), RateLimitPolicy(1, 60), 1).run()

    assert "count toward the subsequent park test" in output.getvalue()


def test_capture_does_not_wait_or_retry_after_429(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_sleep(_seconds: float) -> None:
        pytest.fail("The evidence capture must not wait for a rate-limit reset.")

    curl: CurlResponses = CurlResponses([429, 429])
    monkeypatch.setattr(subprocess, "run", curl.run)
    monkeypatch.setattr("backend.scripts.api_evidence.time.sleep", reject_sleep)
    recorder: CurlRecorder = CurlRecorder("http://localhost:8000", io.StringIO())

    RateLimitEvidence(recorder, RateLimitPolicy(1, 60), RateLimitPolicy(1, 60), 1).run()

    assert len(curl.configs) == 2


def test_capture_stops_if_configured_threshold_does_not_produce_429(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    curl: CurlResponses = CurlResponses([422, 422, 422])
    monkeypatch.setattr(subprocess, "run", curl.run)
    recorder: CurlRecorder = CurlRecorder("http://localhost:8000", io.StringIO())
    evidence: RateLimitEvidence = RateLimitEvidence(
        recorder, RateLimitPolicy(2, 60), RateLimitPolicy(3, 60), 1
    )

    with pytest.raises(RuntimeError, match="did not return 429 within 3 requests"):
        evidence.run()


def test_capture_fails_on_unexpected_park_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    curl: CurlResponses = CurlResponses([429, 404])
    monkeypatch.setattr(subprocess, "run", curl.run)
    recorder: CurlRecorder = CurlRecorder("http://localhost:8000", io.StringIO())
    evidence: RateLimitEvidence = RateLimitEvidence(
        recorder, RateLimitPolicy(1, 60), RateLimitPolicy(2, 60), 1
    )

    with pytest.raises(RuntimeError, match="Park request 1 failed"):
        evidence.run()
