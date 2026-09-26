from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import get_session
from app.models import MangaCache
from app.schemas import MangaRead
from app.services.mangadex import mangadex_client

router = APIRouter(prefix="/manga", tags=["Manga"])
CACHE_EXPIRATION_DAYS = 7

@router.get("/search", response_model=List[MangaRead])
async def search_manga(
    q: str = Query(..., min_length=1, description="Search term for manga title")
):
    try:
        results = await mangadex_client.search_manga(query=q)
        return results
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"MangaDex API error: {str(e)}")

@router.get("/{manga_id}", response_model=MangaRead)
async def get_manga(
    manga_id: str, session: AsyncSession = Depends(get_session)
):
    # Check the cache first
    cached_manga = await session.get(MangaCache, manga_id)
    now = datetime.now(timezone.utc)

    if cached_manga:
        updated_at = cached_manga.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        if now - updated_at < timedelta(days=CACHE_EXPIRATION_DAYS):
            return cached_manga

    # Fetch from MangaDex
    try:
        manga_data = await mangadex_client.fetch_manga_by_id(manga_id)
    except httpx.HTTPStatusError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Manga not found on MangaDex")
        raise HTTPException(status_code=502, detail="Failed to fetch from MangaDex")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="MangaDex network failure")

    # Insert it into the cache
    if cached_manga:
        for key, value in manga_data.items():
            setattr(cached_manga, key, value)
        cached_manga.updated_at = now
        session.add(cached_manga)
    else:
        cached_manga = MangaCache(**manga_data, updated_at=now)
        session.add(cached_manga)

    await session.commit()
    await session.refresh(cached_manga)
    return cached_manga