from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, UserMangaList, ChapterLog, MangaCache
from app.schemas import (
    ListEntryCreateUpdate,
    ListEntryRead,
    ChapterLogCreate,
    ChapterLogRead,
)
from app.routers.manga import get_manga

router = APIRouter(prefix="/list", tags=["User Manga List"])

@router.post("/entry", response_model=ListEntryRead)
async def upsert_list_entry(
    entry_in: ListEntryCreateUpdate, session: AsyncSession = Depends(get_session)
):
    user = await session.get(User, entry_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await get_manga(manga_id=entry_in.manga_id, session=session)

    query = select(UserMangaList).where(
        UserMangaList.user_id == entry_in.user_id,
        UserMangaList.manga_id == entry_in.manga_id,
    )
    res = await session.execute(query)
    entry = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if entry:
        entry.status = entry_in.status
        entry.score = entry_in.score
        entry.last_chapter_read = entry_in.last_chapter_read
        entry.updated_at = now
    else:
        entry = UserMangaList(
            user_id=entry_in.user_id,
            manga_id=entry_in.manga_id,
            status=entry_in.status,
            score=entry_in.score,
            last_chapter_read=entry_in.last_chapter_read,
            updated_at=now,
        )
        session.add(entry)

    await session.commit()
    await session.refresh(entry)
    return entry

@router.get("/{user_id}", response_model=List[ListEntryRead])
async def get_user_list(
    user_id: int, session: AsyncSession = Depends(get_session)
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = select(UserMangaList).where(UserMangaList.user_id == user_id)
    res = await session.execute(query)
    return res.scalars().all()

@router.post("/chapter-log", response_model=ChapterLogRead)
async def create_chapter_log(
    log_in: ChapterLogCreate, session: AsyncSession = Depends(get_session)
):
    user = await session.get(User, log_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await get_manga(manga_id=log_in.manga_id, session=session)

    log_entry = ChapterLog(
        user_id=log_in.user_id,
        manga_id=log_in.manga_id,
        chapter_number=log_in.chapter_number,
        rating=log_in.rating,
        notes=log_in.notes,
    )
    session.add(log_entry)

    query = select(UserMangaList).where(
        UserMangaList.user_id == log_in.user_id,
        UserMangaList.manga_id == log_in.manga_id,
    )
    res = await session.execute(query)
    list_entry = res.scalar_one_or_none()

    if list_entry:
        if log_in.chapter_number > list_entry.last_chapter_read:
            list_entry.last_chapter_read = log_in.chapter_number
            list_entry.updated_at = datetime.now(timezone.utc)
            session.add(list_entry)

    await session.commit()
    await session.refresh(log_entry)
    return log_entry