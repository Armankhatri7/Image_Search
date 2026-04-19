from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.ingest import router as ingest_router
from app.routers.search import router as search_router

app = FastAPI(title="Image Search API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(ingest_router)
app.include_router(search_router)
