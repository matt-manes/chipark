# OpenTelemetry and Grafana Cloud

The backend exports OTLP/HTTP traces, metrics, and logs directly to Grafana
Cloud. It writes structured JSON logs to stdout as well, so they are available
in the Render service Logs view. SQLAlchemy instrumentation adds database spans
to FastAPI request traces. The browser uses Grafana Faro to export browser
errors, console logs, web vitals, and client spans; its tracing instrumentation
propagates W3C trace context to the backend API.

## Configure Grafana Cloud and Render

Create a Grafana Cloud stack with OTLP ingestion enabled. In the Render backend
service, set:

| Variable | Value |
| --- | --- |
| `OTEL_SERVICE_NAME` | `chipark-backend` |
| `OTEL_RESOURCE_ATTRIBUTES` | `deployment.environment=production` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Grafana Cloud's OTLP/HTTP endpoint, usually ending in `/otlp` |
| `OTEL_EXPORTER_OTLP_HEADERS` | `Authorization=Basic <base64 instance-id:token>` from Grafana Cloud |

For local development, set `OTEL_RESOURCE_ATTRIBUTES` to
`deployment.environment=development`. The backend automatically adds
`host.name` using the runtime hostname; you can override it by including
`host.name=<hostname>` in `OTEL_RESOURCE_ATTRIBUTES`.
Keep the OTLP authorization value only in the backend service's secret
environment variables. Do not put it in frontend `VITE_` variables.
These settings can also be placed in `backend/.env`. Signal-specific
`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`,
and `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` values override the shared endpoint;
the matching `*_HEADERS` values override shared headers for that signal.

In the Render frontend build environment, set:

| Variable | Value |
| --- | --- |
| `VITE_FARO_URL` | Grafana Cloud's Faro collection URL |
| `VITE_FARO_API_KEY` | The public ingestion key for that Faro receiver |
| `VITE_API_BASE_URL` | The deployed backend URL |
| `VITE_APP_VERSION` | Optional release identifier |

Vite embeds `VITE_` values into the public frontend bundle. Use only a
receiver-scoped Faro ingestion key, never a Grafana Cloud access token. If
Grafana gives you a private collector credential instead, put a protected
collector or backend proxy between the browser and Grafana. Configure the Faro
receiver to allow the frontend's exact origin and apply its rate limit. The
backend CORS origin list must also include the frontend origin; trace headers
are accepted by the existing CORS middleware.

## SLI, SLO, and alert

The backend records `chipark.api.requests` with HTTP method, route template,
and response status. In Grafana Cloud, use this availability SLI:

```promql
1 -
(
  sum(increase(chipark_api_requests_total{
    service_name="chipark-backend",
    http_response_status_code=~"5.."
  }[30d]))
  /
  sum(increase(chipark_api_requests_total{
    service_name="chipark-backend"
  }[30d]))
)
```

Define the SLO as **at least 99.5% successful requests over a rolling 30-day
window**. For this SLI, 5xx responses are bad events; client errors are not
counted as service availability failures.

Create one Grafana-managed alert rule using this query:

```promql
(
  sum(rate(chipark_api_requests_total{
    service_name="chipark-backend",
    http_response_status_code=~"5.."
  }[5m]))
  /
  sum(rate(chipark_api_requests_total{
    service_name="chipark-backend"
  }[5m]))
) > 0.05
and
sum(rate(chipark_api_requests_total{
  service_name="chipark-backend"
}[5m])) > 0.1
```

Set the condition to alert when the query is true for five minutes. This fires
when at least 5% of requests fail with a server error while the service is
receiving enough traffic to make the ratio meaningful.

The alert must be observed in the **Firing** state to satisfy the assignment.
After deploying and confirming data is arriving, induce a brief, controlled
server-error condition in a staging environment, wait for the pending period,
and capture the alert firing and recovery in Grafana. The code and rule
definition alone do not prove that an alert has fired.

## Verify the telemetry

1. Make a browser API request and open its trace in Grafana. It should include
   the browser request span, FastAPI server span, and SQLAlchemy database span.
2. Find `http_request_completed` in Grafana Logs. The same structured event is
   available in Render's backend service Logs view.
3. Query `chipark_api_requests_total` and confirm `service_name`,
   `http_route`, and `http_response_status_code` labels are present.
4. Confirm the Grafana-managed alert has entered Firing and then returned to
   Normal after the controlled staging incident.
