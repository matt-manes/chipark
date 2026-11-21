import io
import subprocess

import pytest

from backend.scripts.api_evidence import ApiResponse, CurlRecorder


def test_recorder_redacts_response_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="HTTP/1.1 201 Created\nContent-Type: application/json\n\n"
            '{"access_token":"issued-token"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    output: io.StringIO = io.StringIO()
    recorder: CurlRecorder = CurlRecorder("http://localhost:8000", output)
    response: ApiResponse = recorder.request("Register", "POST", "/auth/register", 201)

    assert response.json() == {"access_token": "issued-token"}
    assert "issued-token" not in output.getvalue()
    assert "[REDACTED]" in output.getvalue()


def test_recorder_counts_unexpected_status(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout="HTTP/1.1 403 Forbidden\n\n{}", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    output: io.StringIO = io.StringIO()
    recorder: CurlRecorder = CurlRecorder("http://localhost:8000", output)
    recorder.request("Profile", "GET", "/auth/me", 200)

    assert recorder.failures == 1
    assert "received 403" in output.getvalue()


def test_recorder_redacts_json_escaped_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout="HTTP/1.1 200 OK\n\n{}", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    output: io.StringIO = io.StringIO()
    recorder: CurlRecorder = CurlRecorder("http://localhost:8000", output)
    password: str = 'secret"with\\escapes'
    recorder.add_secret(password)
    recorder.request(
        "Login", "POST", "/auth/login", 200, payload={"password": password}
    )

    assert "[REDACTED]" in output.getvalue()
    assert password not in output.getvalue()


def test_stream_capture_accepts_timeout_after_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[],
            returncode=28,
            stdout="HTTP/1.1 200 OK\n\ndata: event\n\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    output: io.StringIO = io.StringIO()
    recorder: CurlRecorder = CurlRecorder("http://localhost:8000", output)
    recorder.request("Stream", "GET", "/notifications/stream", 200, stream=True)

    assert recorder.failures == 0
