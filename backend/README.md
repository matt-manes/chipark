# ChiPark backend

The ChiPark backend is a Python FastAPI application backed by SQLAlchemy.  
It serves park and ticket data, account and administration operations, notifications, weather conditions, and an MCP server.  
Park records come from the City of Chicago Data Portal; sample accounts, tickets, and notifications are synthetic.

For installation, configuration, local startup, data population, deployment, and observability, see the [runbook](../RUNBOOK.md).  
The [frontend README](../frontend/README.md) describes the browser application.

## API

The application in `app.py` mounts the following routers:

| Route | Purpose | Access |
| --- | --- | --- |
| `/parks` | List parks, get park details, and retrieve weather conditions | Public |
| `/tickets` | Browse, submit, and manage maintenance tickets | Browsing is public; submission requires an account; updates and deletion require an administrator |
| `/auth` | Register, sign in, sign out, and manage the current profile | Registration and sign-in are public; profile and sign-out require an account |
| `/admin/users` | View users and their tickets, change roles, and activate or deactivate accounts | Administrator |
| `/notifications` | List notifications, mark them as read, and receive a live stream | Authenticated account |

Interactive API documentation is available at `/docs` and `/redoc`, with the schema at `/openapi.json`.  
Set `CHIPARK_ENABLE_DOCS=false` to disable these routes.  
The [runbook](../RUNBOOK.md) covers configuration and deployment.

## Authentication and notifications

Accounts support email and password registration and login, as well as Google sign-in when configured.  
The server issues opaque bearer tokens, stores their hashes, and enforces account and administrator permissions on protected operations.  
Signing out revokes the token.

Notifications belong to the authenticated user and can be retrieved or marked as read through the API.  
The authenticated server-sent events stream at `/notifications/stream` supports replay using the `Last-Event-ID` request header.

## Data and configuration

`CHIPARK_DATABASE` environment variable selects SQLite or PostgreSQL.  
PostgreSQL support is included by the default dependency group; omitting that group with `--no-default-groups` when running `uv sync` leaves SQLite available.  
If PostgreSQL is not installed, `uv sync` will fail.  

Weather conditions are retrieved from WeatherAPI and cached according to the configured conditions TTL.  

See the [runbook](../RUNBOOK.md) for environment variables, database setup, data loading, and operational procedures.

## MCP server

The backend mounts a Streamable HTTP MCP server exposing `list_tools`, `list_parks`, `list_tickets`, and `get_park`.  
It also exposes `submit_ticket` to authenticated users and `close_ticket`, `edit_ticket`, and `delete_ticket` to administrators.  
The `list_parks` and `list_tickets` tools reference the ChiPark Explorer MCP App, whose bundle is built by the frontend and served by the backend.  
See the [runbook](../RUNBOOK.md) for the MCP App build and deployment procedure.

## Source layout

| Path | Purpose |
| --- | --- |
| `app.py` | FastAPI application, lifespan, middleware, and router registration |
| `routers/` | HTTP endpoints |
| `services/` | Data, authentication, and notification behavior |
| `repositories/` | Database access and persistence |
| `models/` | Application and database models |
| `clients/` | External service clients |
| `tools/` | Configuration, MCP server, telemetry, and other supporting tools |
| `tests/` | Backend tests |
| `scripts/` | Project maintenance and data-loading commands |

## Development commands

Run these commands from the repository root after installing backend dependencies:

| Command | Purpose |
| --- | --- |
| `uv run --project backend pytest` | Run backend tests |
| `uv run --project backend coverage-suite` | Run tests with coverage and generate reports |
| `uv run --project backend quality-checks` | Run project quality tools, including formatters that can modify files |

The shared database fixture uses a temporary SQLite database by default.  
To use PostgreSQL for that fixture, set `CHIPARK_TEST_PG_URL`, `CHIPARK_TEST_PG_USER`, and `CHIPARK_TEST_PG_PASSWORD`; the database name must contain `test`.  
The fixture creates a separate schema for each test and drops it afterward.
