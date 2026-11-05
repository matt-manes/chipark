import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.applications import Starlette

from backend.repositories import Database, DatabaseFactory
from backend.routers.auth import router as auth_router
from backend.routers.parks import router as parks_router
from backend.routers.tickets import router as tickets_router
from backend.services.auth_service import AuthService
from backend.services.data_service import DataService
from backend.tools.config import Config
from backend.tools.mcp_server import ChiparkMcpServer, McpAsgiApp


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Create shared services and manage the MCP server through shutdown."""
    database: Database = DatabaseFactory.get_database(Config().CHIPARK_DATABASE)
    mcp_server: ChiparkMcpServer = ChiparkMcpServer()
    try:
        data_service: DataService = DataService(database)
        auth_service: AuthService = AuthService(database.session_factory)
        auth_service.bootstrap_admin(
            os.environ.get("CHIPARK_ADMIN_EMAIL"),
            os.environ.get("CHIPARK_ADMIN_PASSWORD"),
        )
        application.state.data_service = data_service
        application.state.auth_service = auth_service
        mcp_server.set_data_service(data_service)
        mcp_application: Starlette = mcp_server.asgi_app()
        mcp_application.state.auth_service = auth_service
        mcp_mount.set_application(mcp_application)
        async with mcp_server.session_manager.run():
            yield
    finally:
        mcp_mount.set_application(None)
        mcp_server.set_data_service(None)
        application.state.data_service = None
        application.state.auth_service = None
        database.close()


app: FastAPI = FastAPI(lifespan=lifespan)
mcp_mount: McpAsgiApp = McpAsgiApp()
app.include_router(auth_router)
app.include_router(parks_router)
app.include_router(tickets_router)


@app.get("/")
async def yeehaw() -> dict[str, str]:
    return {"message": "yeehaw"}


app.mount("/", app=mcp_mount)
