import atexit
import json
import logging
import socket
import time
from datetime import UTC, datetime
from typing import ClassVar, TextIO
from urllib.parse import unquote

from fastapi import FastAPI, Request, Response
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import (  # type: ignore
    SQLAlchemyInstrumentor,
)
from opentelemetry.metrics import Counter, Histogram, Meter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, SpanContext, get_current_span
from sqlalchemy.engine import Engine
from starlette.middleware.base import RequestResponseEndpoint

from backend.tools.config import Config


class JsonStreamHandler(logging.StreamHandler[TextIO]):
    """Mark the console handler used for structured application logs."""


class JsonLogFormatter(logging.Formatter):
    """Format Python log records as structured JSON for Render logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize one log record and its active trace identifiers.

        Parameters
        ----------
        record : logging.LogRecord
            Log record to serialize.

        Returns
        -------
        str
            Compact JSON representation of the record.
        """
        span: Span = get_current_span()
        span_context: SpanContext = span.get_span_context()
        entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": (
                format(span_context.trace_id, "032x") if span_context.is_valid else None
            ),
            "span_id": (
                format(span_context.span_id, "016x") if span_context.is_valid else None
            ),
        }
        for field_name in (
            "http_method",
            "http_route",
            "http_status_code",
            "duration_ms",
        ):
            field_value: object = getattr(record, field_name, None)
            if field_value is not None:
                entry[field_name] = field_value
        if record.exc_info is not None:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, separators=(",", ":"), default=str)


class Telemetry:
    """Configure OpenTelemetry providers and instrument the application."""

    _initialized: ClassVar[bool] = False
    _tracer_provider: ClassVar[TracerProvider | None] = None
    _meter_provider: ClassVar[MeterProvider | None] = None
    _logger_provider: ClassVar[LoggerProvider | None] = None
    _request_counter: ClassVar[Counter | None] = None
    _request_duration: ClassVar[Histogram | None] = None
    _request_logger: ClassVar[logging.Logger] = logging.getLogger("chipark.http")

    @classmethod
    def initialize(cls) -> None:
        """Set up SDK providers, OTLP exporters, and structured console logs."""
        if cls._initialized:
            return

        config: Config = Config()
        service_name: str = config.OTEL_SERVICE_NAME or "chipark-backend"
        resource: Resource = Resource.create(
            cls._get_resource_attributes(
                config.OTEL_RESOURCE_ATTRIBUTES,
                service_name,
            )
        )
        cls._tracer_provider = TracerProvider(resource=resource)
        if cls._has_otlp_endpoint(config.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT, config):
            cls._tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(
                        endpoint=cls._get_otlp_endpoint(
                            config.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT, config
                        ),
                        headers=cls._get_otlp_headers(
                            config.OTEL_EXPORTER_OTLP_TRACES_HEADERS,
                            config.OTEL_EXPORTER_OTLP_HEADERS,
                        ),
                    )
                )
            )
        trace.set_tracer_provider(cls._tracer_provider)

        metric_readers: list[PeriodicExportingMetricReader] = []
        if cls._has_otlp_endpoint(config.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT, config):
            metric_readers.append(
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(
                        endpoint=cls._get_otlp_endpoint(
                            config.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT, config
                        ),
                        headers=cls._get_otlp_headers(
                            config.OTEL_EXPORTER_OTLP_METRICS_HEADERS,
                            config.OTEL_EXPORTER_OTLP_HEADERS,
                        ),
                    )
                )
            )
        cls._meter_provider = MeterProvider(
            resource=resource,
            metric_readers=metric_readers,
        )
        metrics.set_meter_provider(cls._meter_provider)

        cls._logger_provider = LoggerProvider(resource=resource)
        if cls._has_otlp_endpoint(config.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, config):
            cls._logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(
                    OTLPLogExporter(
                        endpoint=cls._get_otlp_endpoint(
                            config.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, config
                        ),
                        headers=cls._get_otlp_headers(
                            config.OTEL_EXPORTER_OTLP_LOGS_HEADERS,
                            config.OTEL_EXPORTER_OTLP_HEADERS,
                        ),
                    )
                )
            )
        root_logger: logging.Logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        if not any(
            isinstance(handler, JsonStreamHandler) for handler in root_logger.handlers
        ):
            console_handler: JsonStreamHandler = JsonStreamHandler()
            console_handler.setFormatter(JsonLogFormatter())
            root_logger.addHandler(console_handler)
        if cls._has_otlp_endpoint(config.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, config):
            root_logger.addHandler(
                LoggingHandler(
                    level=logging.INFO,
                    logger_provider=cls._logger_provider,
                )
            )

        meter: Meter = metrics.get_meter("chipark.http")
        cls._request_counter = meter.create_counter(
            "chipark.api.requests",
            unit="{request}",
            description="HTTP requests handled by the Chipark API.",
        )
        cls._request_duration = meter.create_histogram(
            "chipark.api.request.duration",
            unit="s",
            description="Duration of HTTP requests handled by the Chipark API.",
        )
        cls._initialized = True
        atexit.register(cls.shutdown)

    @classmethod
    def instrument_app(cls, application: FastAPI) -> None:
        """Instrument FastAPI request handling.

        Parameters
        ----------
        application : FastAPI
            Application to instrument.
        """
        cls.initialize()
        FastAPIInstrumentor.instrument_app(application)

    @staticmethod
    def instrument_database(engine: Engine) -> None:
        """Instrument SQLAlchemy operations for one application engine.

        Parameters
        ----------
        engine : Engine
            SQLAlchemy engine to instrument.
        """
        SQLAlchemyInstrumentor().instrument(engine=engine)

    @staticmethod
    def uninstrument_database() -> None:
        """Remove SQLAlchemy instrumentation during application shutdown."""
        SQLAlchemyInstrumentor().uninstrument()

    @classmethod
    async def record_request(
        cls,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Record a request metric and structured completion log.

        Parameters
        ----------
        request : Request
            HTTP request being handled.
        call_next : RequestResponseEndpoint
            Next middleware or application handler in the request chain.

        Returns
        -------
        Response
            Response returned by the next handler.
        """
        start_time: float = time.perf_counter()
        status_code: int = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_seconds: float = time.perf_counter() - start_time
            route: object | None = request.scope.get("route")
            route_path: str = getattr(route, "path", "unmatched")
            attributes: dict[str, str | int] = {
                "http.request.method": request.method,
                "http.route": route_path,
                "http.response.status_code": status_code,
            }
            if cls._request_counter is not None:
                cls._request_counter.add(1, attributes)
            if cls._request_duration is not None:
                cls._request_duration.record(duration_seconds, attributes)
            cls._request_logger.info(
                "http_request_completed",
                extra={
                    "http_method": request.method,
                    "http_route": route_path,
                    "http_status_code": status_code,
                    "duration_ms": round(duration_seconds * 1000, 2),
                },
            )

    @classmethod
    def shutdown(cls) -> None:
        """Flush and shut down the configured SDK providers."""
        provider: TracerProvider | MeterProvider | LoggerProvider | None
        for provider in (
            cls._tracer_provider,
            cls._meter_provider,
            cls._logger_provider,
        ):
            if provider:
                provider.shutdown()

    @staticmethod
    def _has_otlp_endpoint(signal_endpoint: str | None, config: Config) -> bool:
        """Return whether a global or signal-specific OTLP endpoint is configured.

        Parameters
        ----------
        signal_endpoint : str or None
            Endpoint configured for an individual signal.
        config : Config
            Application configuration containing the shared endpoint.

        Returns
        -------
        bool
            Whether either endpoint is configured.
        """
        return bool(signal_endpoint or config.OTEL_EXPORTER_OTLP_ENDPOINT)

    @staticmethod
    def _get_otlp_endpoint(signal_endpoint: str | None, config: Config) -> str | None:
        """Prefer a signal-specific endpoint over the global endpoint.

        Parameters
        ----------
        signal_endpoint : str or None
            Endpoint configured for an individual signal.
        config : Config
            Application configuration containing the shared endpoint.

        Returns
        -------
        str or None
            Signal-specific endpoint, shared endpoint, or ``None`` if neither
            is configured.
        """
        return signal_endpoint or config.OTEL_EXPORTER_OTLP_ENDPOINT

    @staticmethod
    def _get_otlp_headers(
        signal_headers: str | None, shared_headers: str | None
    ) -> dict[str, str] | None:
        """Parse OTLP's comma-separated key/value header configuration.

        Parameters
        ----------
        signal_headers : str or None
            Headers configured for an individual signal.
        shared_headers : str or None
            Headers shared by all signals.

        Returns
        -------
        dict of str to str or None
            Parsed headers, or ``None`` when no headers are configured.

        Raises
        ------
        ValueError
            If a configured header is not a ``key=value`` pair.
        """
        headers_value: str | None = signal_headers or shared_headers
        if headers_value is None:
            return None
        headers: dict[str, str] = {}
        header_value: str
        for header_value in headers_value.split(","):
            name, separator, value = header_value.partition("=")
            if not separator or not name.strip():
                raise ValueError(
                    "OTLP headers must use comma-separated key=value pairs."
                )
            headers[name.strip()] = value.strip()
        return headers

    @classmethod
    def _get_resource_attributes(
        cls,
        configured_attributes: str | None,
        service_name: str,
    ) -> dict[str, str]:
        """Combine configured attributes with service and host identity.

        Parameters
        ----------
        configured_attributes : str or None
            Comma-separated OpenTelemetry resource attributes.
        service_name : str
            Service name assigned to the resource.

        Returns
        -------
        dict of str to str
            Resource attributes including service and host names.
        """
        attributes: dict[str, str] = cls._parse_resource_attributes(
            configured_attributes
        )
        if not attributes.get("host.name"):
            attributes["host.name"] = socket.gethostname()
        attributes["service.name"] = service_name
        return attributes

    @staticmethod
    def _parse_resource_attributes(
        configured_attributes: str | None,
    ) -> dict[str, str]:
        """Parse OpenTelemetry's comma-separated resource attribute setting.

        Parameters
        ----------
        configured_attributes : str or None
            Comma-separated ``key=value`` attributes, with percent-encoded
            values where needed.

        Returns
        -------
        dict of str to str
            Parsed resource attributes.

        Raises
        ------
        ValueError
            If an attribute is not a ``key=value`` pair.
        """
        if not configured_attributes:
            return {}

        attributes: dict[str, str] = {}
        entry: str
        for entry in configured_attributes.split(","):
            name, separator, value = entry.partition("=")
            if not separator or not name.strip():
                raise ValueError(
                    "OTEL_RESOURCE_ATTRIBUTES must use comma-separated key=value pairs."
                )
            attributes[name.strip()] = unquote(value.strip())
        return attributes
