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
park by ID, and submit a ticket for an existing park.
