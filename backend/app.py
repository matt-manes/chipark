from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.repositories import DatabaseFactory
from backend.routers.parks import router as parks_router
from backend.routers.tickets import router as tickets_router
from backend.services.data_service import DataService
from backend.tools.config import Config
from backend.tools.mcp_server import ChiparkMcpServer, McpAsgiApp


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Create shared services and manage the MCP server through shutdown."""
    data_service: DataService = DataService(
        DatabaseFactory.get_database(Config().database)
    )
    application.state.data_service = data_service
    mcp_server: ChiparkMcpServer = ChiparkMcpServer()
    try:
        mcp_server.set_data_service(data_service)
        mcp_mount.set_application(mcp_server.asgi_app())
        async with mcp_server.session_manager.run():
            yield
    finally:
        mcp_mount.set_application(None)
        mcp_server.set_data_service(None)
        application.state.data_service = None
        data_service.close()


app: FastAPI = FastAPI(lifespan=lifespan)
mcp_mount: McpAsgiApp = McpAsgiApp()
app.include_router(parks_router)
app.include_router(tickets_router)


@app.get("/")
async def yeehaw() -> dict[str, str]:
    return {"message": "yeehaw"}


app.mount("/", app=mcp_mount)
