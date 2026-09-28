from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

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

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/", include_in_schema=False)
async def root():
    index_file = os.path.join(frontend_path, "index.html")
    return FileResponse(index_file)