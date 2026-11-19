import asyncio
import json
import logging
import socket
from types import SimpleNamespace
from typing import Protocol, cast
from unittest.mock import Mock

from fastapi import Request, Response
from opentelemetry import trace
from opentelemetry.metrics import Counter, Histogram
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags
from pytest import LogCaptureFixture, MonkeyPatch
from starlette.middleware.base import RequestResponseEndpoint

from backend.tools.telemetry import JsonLogFormatter, Telemetry


class RequestLogRecord(Protocol):
    """Describe request fields added to standard log records."""

    http_method: str
    http_route: str
    http_status_code: int
    duration_ms: float

    def getMessage(self) -> str:
        """Return the record's formatted message."""
        ...


def test_json_log_formatter_includes_structured_request_fields() -> None:
    record: logging.LogRecord = logging.LogRecord(
        name="chipark.http",
        level=logging.INFO,
        pathname="telemetry.py",
        lineno=1,
        msg="http_request_completed",
        args=(),
        exc_info=None,
    )
    request_record: RequestLogRecord = cast(RequestLogRecord, record)
    request_record.http_method = "GET"
    request_record.http_route = "/parks/{park_id}"
    request_record.http_status_code = 200
    request_record.duration_ms = 12.5

    formatted: dict[str, object] = json.loads(JsonLogFormatter().format(record))

    assert formatted["message"] == "http_request_completed"
    assert formatted["severity"] == "INFO"
    assert formatted["http_method"] == "GET"
    assert formatted["http_route"] == "/parks/{park_id}"
    assert formatted["http_status_code"] == 200
    assert formatted["duration_ms"] == 12.5
    assert formatted["trace_id"] is None


def test_json_log_formatter_includes_current_trace_context() -> None:
    record: logging.LogRecord = logging.LogRecord(
        name="chipark.http",
        level=logging.INFO,
        pathname="telemetry.py",
        lineno=1,
        msg="request",
        args=(),
        exc_info=None,
    )
    span_context: SpanContext = SpanContext(
        trace_id=0x1234,
        span_id=0x5678,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )
    span: NonRecordingSpan = NonRecordingSpan(span_context)

    with trace.use_span(span):
        formatted: dict[str, object] = json.loads(JsonLogFormatter().format(record))

    assert formatted["trace_id"] == "00000000000000000000000000001234"
    assert formatted["span_id"] == "0000000000005678"


def test_resource_attributes_include_deployment_environment_and_host() -> None:
    attributes: dict[str, str] = Telemetry._get_resource_attributes(  # type: ignore
        "deployment.environment=development",
        "chipark-backend",
    )

    assert attributes["deployment.environment"] == "development"
    assert attributes["host.name"] == socket.gethostname()
    assert attributes["service.name"] == "chipark-backend"


def test_resource_attributes_allow_configuring_host_name() -> None:
    attributes: dict[str, str] = Telemetry._get_resource_attributes(  # type: ignore
        "deployment.environment=production,host.name=render-service",
        "chipark-backend",
    )

    assert attributes["host.name"] == "render-service"


def test_record_request_logs_and_records_request_metrics(
    monkeypatch: MonkeyPatch, caplog: LogCaptureFixture
) -> None:
    request_counter: Mock = Mock(spec=Counter)
    request_duration: Mock = Mock(spec=Histogram)
    monkeypatch.setattr(Telemetry, "_request_counter", request_counter)
    monkeypatch.setattr(Telemetry, "_request_duration", request_duration)
    route: SimpleNamespace = SimpleNamespace(path="/parks/{park_id}")
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": "/parks/12",
        "headers": [],
        "query_string": b"",
        "server": ("test", 80),
        "client": ("test", 1),
        "scheme": "http",
        "route": route,
    }
    request: Request = Request(scope)
    expected_response: Response = Response(status_code=200)

    async def call_next(_request: Request) -> Response:
        return expected_response

    endpoint: RequestResponseEndpoint = call_next
    with caplog.at_level(logging.INFO, logger="chipark.http"):
        response: Response = asyncio.run(Telemetry.record_request(request, endpoint))

    assert response is expected_response
    assert len(caplog.records) == 1
    record: RequestLogRecord = cast(RequestLogRecord, caplog.records[0])
    assert record.getMessage() == "http_request_completed"
    assert record.http_method == "GET"
    assert record.http_route == "/parks/{park_id}"
    assert record.http_status_code == 200
    request_counter.add.assert_called_once()
    request_duration.record.assert_called_once()
    counter_attributes: dict[str, str | int] = request_counter.add.call_args.args[1]
    duration_attributes: dict[str, str | int] = request_duration.record.call_args.args[
        1
    ]
    assert counter_attributes == duration_attributes
    assert counter_attributes["http.route"] == "/parks/{park_id}"
    assert counter_attributes["http.response.status_code"] == 200
