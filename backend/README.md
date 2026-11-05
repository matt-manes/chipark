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
uv run --project backend python -m backend.tools.populate_parks
```

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

Set `CHIPARK_ADMIN_EMAIL` and `CHIPARK_ADMIN_PASSWORD` before starting the API.
The configured account is created as an administrator or an existing account
with that email is promoted and assigned the configured password. If these
variables are omitted, startup requires an administrator to already exist.

Create an account with `POST /auth/register` or sign in with `POST /auth/login`.
Both return an opaque bearer token that expires after 24 hours. Send it as
`Authorization: Bearer <token>` on authenticated requests. `POST /auth/logout`
revokes the token; `GET /auth/me` returns the current account.

Google sign-in is available through `GET /auth/google`. The configuration keys
in `config.toml` are the same names used for environment variables:
`CHIPARK_DATABASE` and `CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL`. Configure
`CHIPARK_GOOGLE_CLIENT_ID`, `CHIPARK_GOOGLE_CLIENT_SECRET`, and
`CHIPARK_GOOGLE_REDIRECT_URI`; register the backend callback URL
`/auth/google/callback` with Google. The callback redirects to
`CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL` with the bearer token in the URL
fragment. The configured value currently uses the temporary
`http://localhost:3000/auth/callback` placeholder.

Any authenticated user can submit tickets. Only administrators can edit tickets
with `PATCH /tickets/{ticket_id}`, close tickets with
`PATCH /tickets/{ticket_id}/close`, or delete tickets with
`DELETE /tickets/{ticket_id}`. Existing tickets are retained with no owner when
the ownership column is added; new tickets are associated with their submitter.
