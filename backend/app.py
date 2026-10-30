from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.repositories import DatabaseFactory
from backend.routers.parks import router as parks_router
from backend.routers.tickets import router as tickets_router
from backend.services.data_service import DataService
from backend.tools.config import Config


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Create the shared data service and close it during application shutdown."""
    data_service: DataService = DataService(
        DatabaseFactory.get_database(Config().database)
    )
    application.state.data_service = data_service
    try:
        yield
    finally:
        data_service.close()


app: FastAPI = FastAPI(lifespan=lifespan)
app.include_router(parks_router)
app.include_router(tickets_router)


@app.get("/")
async def yeehaw() -> dict[str, str]:
    return {"message": "yeehaw"}
