# Backend

* Install uv

```console
uv init backend --bare
cd backend
uv add "fastapi[standard-no-fastapi-cloud-cli]"
```

new machine:

```console
git clone ****
cd backend
uv sync
cd ..
uv run --project backend python -m backend.scripts.populate_parks
uv run --project backend python -m backend.scripts.populate_tickets
```

From the repo root a default .env file can be generated with `uv run --project backend python -m backend.scripts.new_env`.  
The new file will have all the env vars currently used by the project.  
These values override ones set in the actual environment, so to use the ones set in the actual environment just set the key to have no value in the .env file.

The `backend.repositories` package provides SQLite-backed repositories for the
`Park` and `Ticket` models. By default, `SqliteDatabase` stores data in
`backend/data/chipark.sqlite3`; pass a path or `":memory:"` to select another
database.

The workspace MCP server is configured in the repository-root `.mcp.json`. It
provides tools to list the available tools, list parks and tickets, retrieve a
park by ID, and manage tickets. Ticket submission requires a bearer token, and
the MCP client must send it in the `Authorization` header. Ticket editing,
closing, and deletion require an administrator token.

## Accounts and authorization

Set `CHIPARK_ADMIN_EMAIL` and `CHIPARK_ADMIN_PASSWORD` in the process
environment or `backend/.env` before starting the API. Values in `backend/.env`
override values from the process environment.
The configured account is created as an administrator or an existing account
with that email is promoted and assigned the configured password. If these
variables are omitted, startup requires an administrator to already exist.

Create an account with `POST /auth/register` or sign in with `POST /auth/login`.
Both return an opaque bearer token that expires after 24 hours. Send it as
`Authorization: Bearer <token>` on authenticated requests. `POST /auth/logout`
revokes the token; `GET /auth/me` returns the current account.

Google sign-in is available through `GET /auth/google`. Configure
`CHIPARK_GOOGLE_CLIENT_ID`, `CHIPARK_GOOGLE_CLIENT_SECRET`, and
`CHIPARK_GOOGLE_REDIRECT_URI` in the process environment or `backend/.env`;
register the backend callback URL
`/auth/google/callback` with Google. The callback redirects to
`CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL` with the bearer token in the URL
fragment. The configured frontend callback is
`http://localhost:5173/auth/callback`.

Configuration is loaded from `backend/.env` and the process environment.
`CHIPARK_DATABASE` defaults to `postgresql`,
`CHIPARK_CONDITIONS_TTL` defaults to 900 seconds (15 minutes),
`CHIPARK_CORS_ALLOW_LIST` defaults to `http://localhost:5173` and accepts a
comma-separated list of origins, `CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL` defaults
to `http://localhost:5173/auth/callback`, and
`CHIPARK_PG_URL` defaults to
`postgresql+psycopg2://localhost:5432/chipark`. Optional settings include
`CHIPARK_ADMIN_EMAIL`, `CHIPARK_ADMIN_PASSWORD`, `CHIPARK_WEATHERAPI_KEY`,
`CHIPARK_PG_USER`, `CHIPARK_PG_PASS`, `CHIPARK_GOOGLE_CLIENT_ID`,
`CHIPARK_GOOGLE_CLIENT_SECRET`, `CHIPARK_GOOGLE_REDIRECT_URI`, and
`CHIPARK_TEST_PG_URL`, `CHIPARK_TEST_PG_USER`, and
`CHIPARK_TEST_PG_PASSWORD`.

Authenticated users can update password-based account details with
`PATCH /auth/me`; Google-linked accounts manage their credentials through
Google. `GET /tickets/mine` returns the current user's submitted tickets.
Administrators can reopen tickets with `PATCH /tickets/{ticket_id}/reopen`,
and `GET /tickets/parks/{park_id}/open` returns a park's open tickets.

To use PostgreSQL, set `CHIPARK_DATABASE` to `postgresql`, configure
`CHIPARK_PG_URL` with the SQLAlchemy URL excluding credentials, and provide
`CHIPARK_PG_USER` and `CHIPARK_PG_PASS` through the process environment or
`backend/.env`.

Tests use SQLite by default. To run them against PostgreSQL, set
`CHIPARK_TEST_PG_URL` to a dedicated PostgreSQL test database URL whose database
name contains `test`, and set `CHIPARK_TEST_PG_USER` and
`CHIPARK_TEST_PG_PASSWORD` in the process environment or `backend/.env`. These
test-specific credentials are used instead of the application credentials
`CHIPARK_PG_USER` and `CHIPARK_PG_PASS`. Each test creates a uniquely named
schema and drops it afterward, keeping test tables and sequences isolated from
other runs. Do not point this URL at a development or production database.

Any authenticated user can submit tickets. Only administrators can edit tickets
with `PATCH /tickets/{ticket_id}`, close tickets with
`PATCH /tickets/{ticket_id}/close`, or delete tickets with
`DELETE /tickets/{ticket_id}`. Existing tickets are retained with no owner when
the ownership column is added; new tickets are associated with their submitter.

Ticket updates, closures, and deletions create a persisted notification for the
ticket submitter as part of the same database transaction. Authenticated users
can list their notifications at `GET /notifications`, mark one read with
`PATCH /notifications/{notification_id}/read`, and receive new notifications
over `GET /notifications/stream`. The SSE endpoint requires the bearer token in
the `Authorization` header and polls the database once per second. It supports
`Last-Event-ID` for reconnect replay; clients should use a fetch-based SSE
implementation because browser `EventSource` cannot send the bearer header.
