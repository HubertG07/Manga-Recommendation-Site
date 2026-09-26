from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.routers import users, manga, list_entries

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Manga Tracker & Recommendation API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(users.router)
app.include_router(manga.router)
app.include_router(list_entries.router)

@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "Manga API running correctly"}