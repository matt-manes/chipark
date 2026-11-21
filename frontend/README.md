# ChiPark frontend

The frontend is a React and TypeScript application built with Vite.  
It provides a browser interface for Chicago parks, tickets, accounts, and notifications, plus a separate interactive MCP App.

For installation, configuration, local startup, data population, and deployment, see the [runbook](../RUNBOOK.md).  
The [backend README](../backend/README.md) describes the API and server-side authorization.

## Features

- Browse and search parks; filter by ward, ZIP code, park class, and acreage.
- View a park's details, weather conditions, and open tickets.
- Browse and search tickets, filter by status, and sort results.
- Register or sign in with email and password or Google, submit tickets, and manage a profile.
- Receive ticket notifications and mark them as read.
- As an administrator, edit, close, or reopen tickets and manage users.

Park and ticket search, filtering, sorting, and pagination run in the browser on data fetched from the API.  
The parks, tickets, and users pages provide a reset button to clear searches and filters and restore the default sorting.  
The backend enforces authorization for protected operations.

## Navigation and authentication

`src/navigation/AppRoute.ts` resolves browser paths and their access requirements.  
Public pages include `/parks`, `/parks/{id}`, `/tickets`, `/login`, and `/register`.  
Ticket submission and profiles require an authenticated account; ticket editing and user administration require an administrator.

`src/navigation/BrowserRoute.ts` stores the application bearer token in browser local storage.  
For Google sign-in, the backend redirects to `/auth/callback` with a token in the URL fragment; the frontend stores the token and removes the fragment from the address bar.  
`src/api/ChiparkApiClient.ts` sends the token in the `Authorization` header for authenticated requests.

The notification stream uses `fetch` to send the bearer token and `Last-Event-ID` when reconnecting.  
Notifications are merged by ID in `src/App.tsx`.

## Source layout

| Path | Purpose |
| --- | --- |
| `src/App.tsx` | Application state, navigation, authentication, and notifications |
| `src/api/` | API client and response types |
| `src/pages/` | Park, ticket, account, profile, and administration pages |
| `src/components/` | Shared layout and UI components |
| `src/navigation/` | Route resolution and token storage |
| `src/utils/catalog.ts` | Client-side filtering and sorting |
| `src/mcp-app/` | Interactive MCP App entry point |
| `src/config.ts` | Frontend environment configuration |
| `src/telemetry.ts` | Grafana Faro browser telemetry |
| `tests/` | Node-based frontend tests |

## Configuration and commands

The [frontend configuration section of the runbook](../RUNBOOK.md#frontend) documents the `VITE_` variables, defaults, and Faro configuration.  
Vite embeds these values at build time.  
The static host must serve `index.html` for client-side routes, including `/auth/callback`; see [frontend deployment](../RUNBOOK.md#5-build-and-deploy-the-frontend).

Run these commands from the repository root after installing dependencies:

| Command | Purpose |
| --- | --- |
| `npm --prefix frontend run dev` | Start the Vite development server |
| `npm --prefix frontend run build` | Type-check and build the site and MCP App |
| `npm --prefix frontend run preview` | Preview the production site build |
| `npm --prefix frontend run lint` | Run ESLint |
| `npm --prefix frontend test` | Run the Node-based frontend tests |

## MCP App

`src/mcp-app/ChiparkMcpApp.tsx` implements the ChiPark Explorer for an MCP Apps-compatible host.  
It calls the server's `list_parks` and `list_tickets` tools to browse and refresh data.  
The frontend build outputs `dist/mcp-app/mcp-app.html`; the backend serves this file as the `ui://chipark/explorer.html` resource.  
See the [runbook](../RUNBOOK.md#5-mcp-app) for its deployment requirements.
