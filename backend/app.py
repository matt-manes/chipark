from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.routing import Route

from backend.repositories import Database, DatabaseFactory
from backend.routers.admin_users import router as admin_users_router
from backend.routers.auth import router as auth_router
from backend.routers.notifications import router as notifications_router
from backend.routers.parks import router as parks_router
from backend.routers.tickets import router as tickets_router
from backend.services.auth_service import AuthService
from backend.services.data_service import DataService
from backend.tools.config import Config
from backend.tools.http_errors import ApiCORSMiddleware, HttpErrorResponses
from backend.tools.mcp_server import ChiparkMcpServer, McpAsgiApp
from backend.tools.rate_limiting import (
    IpRateLimitCoordinator,
    IpRateLimitMiddleware,
)
from backend.tools.telemetry import Telemetry


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Manage database-backed services for the application lifespan.

    Parameters
    ----------
    application : FastAPI
        Application receiving the shared service instances.

    Yields
    ------
    None
        Control to the running application while its services are available.
    """
    database: Database = DatabaseFactory.get_database(Config().CHIPARK_DATABASE)
    mcp_server: ChiparkMcpServer = ChiparkMcpServer()
    cleanup_tasks_started: bool = False
    database_instrumented: bool = False
    try:
        Telemetry.instrument_database(database.engine)
        database_instrumented = True
        data_service: DataService = DataService(database)
        auth_service: AuthService = AuthService(database.session_factory)
        config: Config = Config()
        auth_service.bootstrap_admin(
            config.CHIPARK_ADMIN_EMAIL,
            config.CHIPARK_ADMIN_PASSWORD,
        )
        application.state.data_service = data_service
        application.state.auth_service = auth_service
        mcp_server.set_data_service(data_service)
        mcp_application: Starlette = mcp_server.asgi_app()
        mcp_application.state.auth_service = auth_service
        mcp_mount.set_application(mcp_application)
        await rate_limit_coordinator.start_cleanup_tasks()
        cleanup_tasks_started = True
        async with mcp_server.session_manager.run():
            yield
    finally:
        if cleanup_tasks_started:
            await rate_limit_coordinator.stop_cleanup_tasks()
        mcp_mount.set_application(None)
        mcp_server.set_data_service(None)
        application.state.data_service = None
        application.state.auth_service = None
        if database_instrumented:
            Telemetry.uninstrument_database()
        database.close()


class ApplicationFactory:
    """Create the FastAPI application with configurable documentation."""

    @staticmethod
    def create(docs_enabled: bool) -> FastAPI:
        """Create the application with its documentation routes configured.

        Parameters
        ----------
        docs_enabled : bool
            Whether to expose the documentation and OpenAPI schema.

        Returns
        -------
        FastAPI
            Application with documentation routes configured.
        """
        application: FastAPI = FastAPI(
            lifespan=lifespan,
            docs_url="/docs" if docs_enabled else None,
            redoc_url="/redoc" if docs_enabled else None,
            openapi_url="/openapi.json" if docs_enabled else None,
        )
        application.add_exception_handler(
            HTTPException, HttpErrorResponses.handle_http_exception
        )
        application.add_exception_handler(
            Exception, HttpErrorResponses.handle_unexpected_exception
        )
        return application


app: FastAPI = ApplicationFactory.create(Config().CHIPARK_ENABLE_DOCS)
rate_limit_coordinator: IpRateLimitCoordinator = IpRateLimitCoordinator(
    auth_policy=Config().CHIPARK_RATE_LIMIT_AUTH,
    global_policy=Config().CHIPARK_RATE_LIMIT_GLOBAL,
)
app.add_middleware(
    ApiCORSMiddleware,
    allow_origins=list(Config().cors_allow_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    IpRateLimitMiddleware,
    rate_limit_coordinator=rate_limit_coordinator,
)
app.middleware("http")(Telemetry.record_request)
mcp_mount: McpAsgiApp = McpAsgiApp()
app.include_router(auth_router)
app.include_router(admin_users_router)
app.include_router(notifications_router)
app.include_router(parks_router)
app.include_router(tickets_router)
Telemetry.instrument_app(app)


@app.get("/")
async def yeehaw() -> dict[str, str]:
    return {"message": "yeehaw"}


app.router.routes.append(Route("/mcp", endpoint=mcp_mount, include_in_schema=False))
