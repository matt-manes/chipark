from fastapi import FastAPI

from backend.routers.parks import router as parks_router
from backend.routers.tickets import router as tickets_router

app: FastAPI = FastAPI()
app.include_router(parks_router)
app.include_router(tickets_router)


@app.get("/")
async def yeehaw() -> dict[str, str]:
    return {"message": "yeehaw"}
