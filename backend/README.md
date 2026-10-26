# Backend

* Install uv

```console
uv init backend --bare
cd backend
uv add "fastapi[standard-no-fastapi-cloud-cli]"
```

The `backend.repositories` package provides SQLite-backed repositories for the
`Park` and `Ticket` models. By default, `SqliteDatabase` stores data in
`backend/data/chipark.sqlite3`; pass a path or `":memory:"` to select another
database.
