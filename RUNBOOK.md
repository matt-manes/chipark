# Chipark runbook

This guide covers local development and deployment to a hosting service.
Commands work in Windows, macOS, and Linux terminals unless otherwise noted.
Run commands from the repository root unless a different directory is stated.

## Requirements

- Git.
- Python 3.11 or later and [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Node.js 24 and npm.
- PostgreSQL if using it locally, or access to a managed PostgreSQL database.
  SQLite is also supported for local development.
- A [WeatherAPI](https://www.weatherapi.com/) key for weather data.  
  See the
  known issue below.

Google sign-in, MCP App rendering, and Grafana are optional.

## Local development

### 1. Clone and install

```text
git clone https://github.com/matt-manes/chipark.git
cd chipark
```

To support both SQLite and PostgreSQL (select the database with
`CHIPARK_DATABASE` in `backend/.env`):

```text
uv sync --project backend --locked
```

For a SQLite-only installation:

```text
uv sync --project backend --locked --no-default-groups
```

Install the frontend dependencies:

```text
npm --prefix frontend ci
```

The PostgreSQL group installs `psycopg2`.  
If a wheel is unavailable for your
platform, its installation requires a C compiler and PostgreSQL development
files, including `pg_config`.

### 2. Configuration

All keys set in an .env file override the same key if it is present in the process environment.
To use the process environment variable, set the key in the .env file equal to nothing (e.g. `CHIPARK_DATABASE=`)
or remove it from the file.

#### Backend

Create `backend/.env` with:

```dotenv
CHIPARK_DATABASE=postgresql
CHIPARK_CONDITIONS_TTL=900
CHIPARK_CORS_ALLOW_LIST=http://localhost:5173
CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL=http://localhost:5173/auth/callback
CHIPARK_PG_URL=postgresql+psycopg2://localhost:5432/chipark
CHIPARK_PG_USER=postgres
CHIPARK_PG_PASS=your-database-password
CHIPARK_ADMIN_EMAIL=admin@example.com
CHIPARK_ADMIN_PASSWORD=your-admin-password
CHIPARK_WEATHERAPI_KEY=your-weatherapi-key
CHIPARK_RATE_LIMIT_AUTH=5/minute
CHIPARK_RATE_LIMIT_GLOBAL=60/minute
CHIPARK_ENABLE_DOCS=true
```

`CHIPARK_ENABLE_DOCS` defaults to `true`.  
Set it to `false` to disable
`/docs`, `/redoc`, and `/openapi.json`, then restart the backend.

Replace the credentials with your own.  
The admin password must be 6-128
characters.  
The admin user will be created with these credentials the first time the server runs if
one doesn't already exist.  
Remove the weather key line if you do not have a key; weather will
be unavailable.  
`CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL` is required even if
Google sign-in is not configured.  

The `CHIPARK_CORS_ALLOW_LIST` can have multiple urls, provided that they are comma separated.
This is also true for the value when read from the process environment.

For a local PostgreSQL server, create a database named `chipark` and use the
username and password for a role allowed to create and modify tables.  
For
example, if the `postgres` role has database-creation privileges:

```text
createdb -h localhost -p 5432 -U postgres chipark
```

`createdb` is supplied by the PostgreSQL client tools.  
Use your installation's
actual host, port, role, and database name if different.  
The application creates
the tables on first connection; it does not create the PostgreSQL database or
migrate existing tables.

For a remote PostgreSQL database, including Supabase, use the connection
instructions in [PostgreSQL connection settings](#postgresql-connection-settings).

For SQLite, change `CHIPARK_DATABASE` to `sqlite`.  
SQLite stores its database at
`backend/data/chipark.sqlite3`.

The first backend startup creates the configured administrator.  
While both
admin settings remain configured, every startup reapplies that password and
role.  
If both are omitted later, an administrator must already exist.

The alternative generator
`uv run --project backend --no-sync python -m backend.scripts.new_env` creates
`backend/.env`, but leaves some required settings blank.  
Fill them in before
starting the application.  
Values in `backend/.env`, including empty values,
override process environment variables; remove a line's value to use its process
environment value.  
Restart the backend after changes.

#### Frontend

The frontend reads Vite environment variables from `frontend/.env`.  
Only
variables prefixed with `VITE_` are exposed to the browser.  
These values are
embedded in the frontend bundle, so do not put secrets in this file.  
The
supported options are:

| Variable | Purpose | Default |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Backend API origin | `http://127.0.0.1:8000` |
| `VITE_FARO_URL` | Grafana Faro collector URL; configure together with `VITE_FARO_API_KEY` | Unset |
| `VITE_FARO_API_KEY` | Public ingestion key for the Faro receiver; configure together with `VITE_FARO_URL` | Unset |
| `VITE_APP_NAME` | Frontend application name | `chipark-frontend` |
| `VITE_APP_VERSION` | Frontend release identifier | `development` |

For example, create `frontend/.env` with:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

For Grafana Faro, add both `VITE_FARO_URL` and `VITE_FARO_API_KEY`.  
Use only a
receiver-scoped public ingestion key.  
Do not configure a Grafana access token
or any other secret in a `VITE_` variable.  
Restart the frontend development
server after changing this file; rebuild the frontend after changing values
used by a production build.

### 3. Populate data

To populate the database:

```text
uv run --project backend --no-sync python -m backend.scripts.populate_all_data
```

The script loads parks from the included GeoJSON and skips park numbers already in the
configured database.  
It then takes `backend/data/sample-users.json` and registers each email as an account, generating a password.
The accounts and their passwords are then written to `backend/data/registered-sample-users.json`.  
If this script has already been run before it will fail unless the database is reset.  
After registering accounts, the tickets in `backend/data/synthetic-tickets.json` will be added to the database
with a random user id assigned to each ticket.

### 4. Start the backend and frontend

Start the backend from the repository root:

```text
uv run --project backend --no-sync uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, from the repository root:

```text
npm --prefix frontend run dev
```

Open `http://localhost:5173`.
If the frontend origin changes, add the exact new origin to
`CHIPARK_CORS_ALLOW_LIST`.  
Restart the affected process after configuration
changes.

Open `http://127.0.0.1:8000/parks` to check the data and
`http://127.0.0.1:8000/docs` for the API documentation.  
Sign in with the
administrator credentials or register through the frontend.

### 5. MCP App

The interactive MCP App requires a built frontend bundle:

```text
npm --prefix frontend run build
```

The backend serves `frontend/dist/mcp-app/mcp-app.html` as an MCP resource.
The repository's `.mcp.json` points to `http://127.0.0.1:8000/mcp`.  
An
MCP Apps-compatible host is required to render the interactive UI.  
Normal MCP
tools can be used without the UI bundle.

## PostgreSQL connection settings

The database can run locally or on a separate provider.  
The backend connects
directly using PostgreSQL, not the provider's HTTP API.  
Obtain the database
host, port, database name, username, and password from your provider.

Set these values in `backend/.env` locally, or in your hosting service's
backend environment for deployment:

```dotenv
CHIPARK_DATABASE=postgresql
CHIPARK_PG_URL=postgresql+psycopg2://DATABASE_HOST:DATABASE_PORT/DATABASE_NAME
CHIPARK_PG_USER=DATABASE_USERNAME
CHIPARK_PG_PASS=DATABASE_PASSWORD
```

Replace the placeholders with the actual connection details.  
Keep credentials
out of `CHIPARK_PG_URL`; the application inserts `CHIPARK_PG_USER` and
`CHIPARK_PG_PASS` into the connection URL itself.

The database must be reachable from the backend and any machine used for
population.  
Check network restrictions, the supported IP version, and the
database role's permissions if connection or table creation fails.

### Supabase example

Set up a Supabase project.
In the Supabase project, open **Connect** and select `Direct`.
The `Connection Method` should be `Transaction pooler` and `Type` should be `URI`.
From the `Connection String` below, copy/paste the `host`, `port` and `database` parameters into
the `CHIPARK_PG_URL` env var formatted as `postgresql+psycopg2://[HOST]:[PORT]/[DATABASE]`.
Copy the `user` parameter and use it as the `CHIPARK_PG_USER` env var.
For `CHIPARK_PG_PASS` use the database password Supabase provides when creating the database.

## Deployment

Deploy the backend and frontend separately, or package them together if your
host supports both.  
The backend needs a persistent Python ASGI process, network
access to PostgreSQL, and a writable connection to its database.  
The frontend
needs a static-file host with an SPA fallback.  
The database can be hosted
independently, such as on Supabase.

The project uses a Render web service for the backend and a separate Render
static site for the frontend, with PostgreSQL hosted separately.  
The Render
instructions below describe a reproducible configuration, not an export of
the live dashboard settings.  
The repository has no Render Blueprint.

For separate staging and production environments, use separate services,
databases, and secrets.  
Promote a verified revision to production using the
configured deployment workflow.

### 1. Configure the database

Provision PostgreSQL and configure the backend using the settings above.  
The
database role needs permission to create tables and perform the application's
read/write operations.  
Use a persistent database and configure backups through
your database provider.

The SQLite path is fixed within the backend directory.  
If used in a hosted
environment, it must be backed by persistent storage at that path.  
An
ephemeral filesystem loses the database on redeploy or restart; PostgreSQL is
the safer choice for hosted deployments.

### 2. Build and configure the backend

Use the repository root as the backend working directory.  
Install Python and
uv on the host or in the build image, then run:

```text
uv sync --project backend --locked
```

Set these backend environment variables through your hosting service:

| Variable | Value |
| --- | --- |
| `CHIPARK_DATABASE` | `postgresql` |
| `CHIPARK_PG_URL` | Credential-free PostgreSQL URL |
| `CHIPARK_PG_USER` | Database username |
| `CHIPARK_PG_PASS` | Database password |
| `CHIPARK_ADMIN_EMAIL` | Initial administrator email |
| `CHIPARK_ADMIN_PASSWORD` | Initial administrator password |
| `CHIPARK_CONDITIONS_TTL` | Weather cache TTL in seconds, such as `900` |
| `CHIPARK_CORS_ALLOW_LIST` | Actual frontend origin, such as `https://csc436.xyz` |
| `CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL` | Actual frontend origin followed by `/auth/callback` |
| `CHIPARK_WEATHERAPI_KEY` | WeatherAPI key, if available |
| `CHIPARK_RATE_LIMIT_AUTH` | Optional; defaults to `5/minute` |
| `CHIPARK_RATE_LIMIT_GLOBAL` | Optional; defaults to `60/minute` |
| `CHIPARK_ENABLE_DOCS` | Set to `false` to disable API documentation routes |

Separate multiple CORS origins with commas; include the scheme and any port,
but no path or trailing slash.  
Do not deploy a local `backend/.env` over these
environment settings: its values take precedence.

To serve the MCP App, install Node and npm in the build environment and run:

```text
npm --prefix frontend ci
npm --prefix frontend run build
```

Preserve `frontend/dist/mcp-app/mcp-app.html` at that relative path in the
backend runtime filesystem.  
A separate static frontend deployment does not
automatically provide the file to the backend.  
The backend starts without the
bundle, but requesting the MCP App resource fails.

Start the ASGI service on the interface and port required by your host.  
For
example, with a POSIX shell and a host-provided `PORT`:

```sh
uv run --project backend --no-sync uvicorn backend.app:app --host 0.0.0.0 --port "$PORT"
```

On Windows, replace `"$PORT"` with the configured port number, for example
`8000`.  
Configure the host's HTTP health check as `GET /`, if supported.
Configure its reverse proxy to support streaming for notifications and MCP.

#### On Render

***NOTE:*** uv is not available in the environment unless Render detects a `uv.lock` file in the root of the repo
which is why there is an empty `uv.lock` present in the repo root.  

In the project view add a new web service with `https://github.com/matt-manes/chipark` as the repo.  
It should auto detect the language as Python3.  
Set the Region appropriately.  
Change the name from `chipark` to something like `api-chipark` so that the frontend can use `chipark`.  
Leave the root directory empty.  
For the build command use `uv sync --project backend --locked`.  
For the start command use `uv run --project backend uvicorn app:app --host 0.0.0.0 --port $PORT`.  

Add the backend variables specified earlier in the Environment Variables section.  
This can be done manually or from a .env file.

**To use a custom domain**:

After deploying, go to "My project" and select the web service that was just deployed.  
From the sidebar click on Settings and use the custom domains section to add a subdomain (`api.csc436.xyz` in this case).  
This will also require an ALIAS DNS record in your registrar to point the domain at the Render url.  
e.g.

|Name|Type|Content|
|---|---|---|
|api.csc436.xyz|ALIAS|api-chipark.onrender.com|

### 3. Populate data

Run this once from the deployed backend environment or from a separately
configured checkout such as your local machine that can reach the production database:

```text
uv run --project backend --no-sync python -m backend.scripts.populate_all_data
```

This loads the Chicago park data and synthetic users and tickets into the
configured production database.  
As noted in the local population instructions,
the user and ticket population steps are not safe to repeat.

### 4. Build and deploy the frontend

In the frontend build environment, set `VITE_API_BASE_URL` to the public
backend HTTPS origin, for example `https://api.csc436.xyz`.  
Then run:

```text
npm --prefix frontend ci
npm --prefix frontend run build
```

Publish `frontend/dist` to a static-file host.  
Configure an SPA fallback that
serves `index.html` for paths that do not match an existing file, including
`/auth/callback`, without redirecting the browser to a different URL.

Vite embeds `VITE_API_BASE_URL` at build time.  
Rebuild and redeploy after
changing it.  
Ensure the backend CORS allow-list includes the actual frontend
origin.

#### On Render

Create a Static Site from the same repository and desired branch.  
Set the root directory to `frontend`, the build command to `npm ci && npm run build`,
and the publish directory to `dist`.  

In Environment Variables, set `VITE_API_BASE_URL` to the backend's public HTTPS origin before building.  
Configure optional Faro variables as described under [OpenTelemetry and Grafana Cloud](#opentelemetry-and-grafana-cloud).  

After deploying, go to "My project" and select the static site that was just deployed.  
On the side bar, click "Redirects/Rewrites".  
Add a rule with the values:  

|Source|Destination|Action|
|---|---|---|
|/*|/index.html|Rewrite|

This is to handle when something like `[DOMAIN]/parks` is entered directly into the browser's address bar.  

**To use a custom domain**:

From the sidebar click on Settings and use the custom domains section to add a domain (`csc436.xyz` in this case).  
This will also require an ALIAS DNS record in your registrar to point the domain at the Render url.  
e.g.

|Name|Type|Content|
|---|---|---|
|csc436.xyz|ALIAS|chipark.onrender.com|

##### Redeploy to Render on commit

Render doesn't automatically redeploy on a commit to main for public GitHub repos.  
However they do provide a secret url to trigger a redeploy.  
These can be found in the settings for each service/site under the **Deploy** section.  
If they are added to the GitHub repo they can be used by the `.github/workflows/deploy.yml` action to automatically
trigger a redeploy when a commit is pushed to main.  
On the GitHub repository page, go to `Settings->Secrets and variables->Actions`.  
Add the frontend hook url as `RENDER_FRONTEND_HOOK_URL` and the backend hook url as `RENDER_BACKEND_HOOK_URL`.

### 5. Domains and caching

Render manages caching for static sites, so the frontend is already behind a cdn without further steps.  

Configure custom domains and TLS with your hosting and DNS providers.  
If using
a CDN for the API, cache only explicitly selected public GET endpoints.
Bypass authenticated responses, mutations, notifications/SSE, and `/mcp`.
Cached park responses may remain stale until their TTL expires or they are
purged.

#### On Render

Add custom domains to the corresponding services and follow the dashboard's
DNS instructions.  
Render provisions and renews TLS certificates and redirects
HTTP to HTTPS.  
Update the backend CORS and OAuth settings and the frontend API
URL to match the actual origins, then redeploy after changing environment variables.

#### On Cloudflare

Cloudflare manages DNS for the registered domain and can proxy requests to the
backend on Render.  
The frontend uses the main domain, while a separate API
hostname directs backend requests through Cloudflare to the Render web
service.  
Check the Cloudflare dashboard for the actual hostnames, rules, and
TTLs; the values below are examples:

1. In Cloudflare, select **Domains**, add the registered domain, and replace
   the nameservers at the registrar with the nameservers Cloudflare assigns.
   Wait for the domain to become active.  
   Recreate the frontend DNS record in
   **DNS > Records**, pointing it to the frontend Render hostname if Cloudflare is unable to do it automatically.
2. In Render, add the API hostname (for example, `api.csc436.xyz`) under the
   backend service's **Settings > Custom Domains**.  
   In Cloudflare DNS, add an
   `api` CNAME pointing to `api-chipark.onrender.com`, or the backend hostname
   currently shown by Render.  
   Use **DNS only** until Render verifies the
   domain and issues its certificate, then enable **Proxied**.
3. In Cloudflare **SSL/TLS > Overview**, select **Full (strict)** once the
   Render certificate is valid.  
   In the frontend's Render environment, set
   `VITE_API_BASE_URL` to the proxied API HTTPS origin and redeploy.  
   Using the
   `onrender.com` API URL directly bypasses the custom Cloudflare hostname.
   Update `CHIPARK_CORS_ALLOW_LIST` to the exact frontend origin and, if using
   Google sign-in, set `CHIPARK_GOOGLE_REDIRECT_URI` to the API origin plus
   `/auth/google/callback` and `CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL` to the
   frontend origin plus `/auth/callback`.
4. In **Caching > Cache Rules**, configure a public park GET rule for
   `/parks` and numeric park IDs:

   ```text
   http.host eq "api.csc436.xyz"
   and http.request.method eq "GET"
   and (
   http.request.uri.path eq "/parks"
    or (
      http.request.uri.path wildcard "/parks/*"
      and not ends_with(http.request.uri.path, "/conditions")
     )
   )
   ```

   Replace the hostname with the actual API hostname.  
   For example, set **Eligible for cache**, an edge TTL of 300 seconds,
   and **Bypass cache** for the browser TTL; verify the values in the dashboard.
   This expression excludes park conditions.
5. Add an explicit bypass rule for all other requests to the API hostname,
   including authentication, tickets, admin routes, notifications/SSE, MCP,
   and writes.  
   Keep it disjoint from the public park GET rule; do not
   shared-cache authenticated or personalized responses.

   e.g.

   ```text
   http.host eq "api.csc436.xyz"
   and not (
   http.request.method eq "GET"
   and (
    http.request.uri.path eq "/parks"
    or  http.request.uri.path wildcard "/parks/*"
    )
   )
   ```

Check delegation with `dig NS csc436.xyz` against independent resolvers, and
check the API rule by requesting `/parks` twice through the proxied hostname:

```sh
curl -sS -D - -o /dev/null https://api.csc436.xyz/parks
curl -sS -D - -o /dev/null https://api.csc436.xyz/parks
```

Look for `CF-Cache-Status: MISS` followed by `HIT`; an existing cached response
may already be a hit.  
Check an authenticated endpoint as well and confirm its
response is not shared-cached.  
Substitute the actual domain and API hostname
if different.

### 6. Verify

1. Open the backend `/parks` URL and confirm it returns park data.
2. Open the frontend and confirm parks load.
3. Sign in, open a park, and submit a ticket.  
   Confirm it appears in the ticket
   list; sign in as the administrator to manage it.
4. Open a frontend detail URL directly and refresh it to check the SPA fallback.
5. If using the MCP App, connect a compatible host to the backend `/mcp`
   endpoint and invoke `list_parks`.

## Optional integrations

### Google sign-in

Create a Google OAuth **Web application** client and configure the consent
screen.  
Add the exact frontend origin under **Authorized JavaScript origins**
and the backend callback under **Authorized redirect URIs**:

| Environment | Frontend origin | Backend redirect URI |
| --- | --- | --- |
| Local | `http://localhost:5173` | `http://127.0.0.1:8000/auth/google/callback` |
| Deployment | Your frontend HTTPS origin | Your backend HTTPS origin followed by `/auth/google/callback` |

Configure the backend with the client ID, secret, and matching URLs:

```dotenv
CHIPARK_GOOGLE_CLIENT_ID=your-client-id
CHIPARK_GOOGLE_CLIENT_SECRET=your-client-secret
CHIPARK_GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback
CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL=http://localhost:5173/auth/callback
```

Use the public deployment URLs in production (e.g. `CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL=https://csc436.xyz/auth/callback`).  
Add test users in Google if the
consent screen is in testing mode.  
Restart or redeploy after changes.

### OpenTelemetry and Grafana Cloud

The backend exports OTLP/HTTP traces, metrics, and logs directly to Grafana
Cloud.  
It writes structured JSON logs to stdout as well, so they are available
in the Render service Logs view.  
SQLAlchemy instrumentation adds database spans
to FastAPI request traces.  
The browser uses Grafana Faro to export browser
errors, console logs, web vitals, and client spans; its tracing instrumentation
propagates W3C trace context to the backend API.

#### Configure Grafana Cloud and Render

Create a Grafana Cloud stack with OTLP ingestion enabled.  
In the Render backend
service, set:

| Variable | Value |
| --- | --- |
| `OTEL_SERVICE_NAME` | `chipark-backend` |
| `OTEL_RESOURCE_ATTRIBUTES` | `deployment.environment=production` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Grafana Cloud's OTLP/HTTP endpoint, usually ending in `/otlp` |
| `OTEL_EXPORTER_OTLP_HEADERS` | `Authorization=Basic <base64 instance-id:token>` from Grafana Cloud |

For local development, set `OTEL_RESOURCE_ATTRIBUTES` to
`deployment.environment=development`.  
The backend automatically adds
`host.name` using the runtime hostname; you can override it by including
`host.name=<hostname>` in `OTEL_RESOURCE_ATTRIBUTES`.
Keep the OTLP authorization value only in the backend service's secret
environment variables.  
Do not put it in frontend `VITE_` variables.
These settings can also be placed in `backend/.env`.  
Signal-specific
`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`,
and `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` values override the shared endpoint;
the matching `*_HEADERS` values override shared headers for that signal.

In the Render frontend build environment, set:

| Variable | Value |
| --- | --- |
| `VITE_FARO_URL` | Grafana Cloud's Faro collection URL |
| `VITE_FARO_API_KEY` | The public ingestion key for that Faro receiver |
| `VITE_API_BASE_URL` | The deployed backend URL |
| `VITE_APP_NAME` | Optional frontend application name; defaults to `chipark-frontend` |
| `VITE_APP_VERSION` | Optional release identifier |

Vite embeds `VITE_` values into the public frontend bundle.  
Use only a
receiver-scoped Faro ingestion key, never a Grafana Cloud access token.  
If
Grafana gives you a private collector credential instead, put a protected
collector or backend proxy between the browser and Grafana.  
Configure the Faro
receiver to allow the frontend's exact origin and apply its rate limit.  
The
backend CORS origin list must also include the frontend origin; trace headers
are accepted by the existing CORS middleware.

#### Verify the telemetry

1. Make a browser API request and open its trace in Grafana.  
   It should include
   the browser request span, FastAPI server span, and SQLAlchemy database span.
2. Find `http_request_completed` in Grafana Logs.  
   The same structured event is
   available in Render's backend service Logs view.
3. Query `chipark_api_requests_total` and confirm `service_name`,
   `http_route`, and `http_response_status_code` labels are present.
