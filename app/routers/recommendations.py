from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, MangaCache, UserMangaList, RecommendationFeedback
from app.schemas import RecommendationRead, FeedbackCreate
from app.services.recommender import manga_recommender
from app.services.mangadex import mangadex_client

import random

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.get("/{user_id}", response_model=List[RecommendationRead])
async def get_recommendations(
    user_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    refresh: bool = Query(default=False)
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User Not Found")

    if refresh:
        try:
            offset = random.randint(0, 100)
            new_candidates = await mangadex_client.search_manga(query="", limit=20, offset=offset)
            for m_data in new_candidates:
                existing = await session.get(MangaCache, m_data["manga_id"])
                if not existing:
                    session.add(MangaCache(**m_data))
            await session.commit()
        except Exception:
            pass

    cached_res = await session.execute(select(MangaCache))
    all_cached_manga = list(cached_res.scalars().all())

    user_list_res = await session.execute(
        select(UserMangaList).where(UserMangaList.user_id == user_id)
    )    
    user_list_entries = list(user_list_res.scalars().all())

    feedback_res = await session.execute(
        select(RecommendationFeedback).where(RecommendationFeedback.user_id == user_id)
    )
    feedback_entries = list(feedback_res.scalars().all())

    recommendations = manga_recommender.build_recommendation(
        all_cached_manga=all_cached_manga,
        user_list_entries=user_list_entries,
        feedback_entries=feedback_entries,
        top_n=limit,
        shuffle=refresh,
    )

    return [
        RecommendationRead(
            manga_id=manga.manga_id,
            title=manga.title,
            cover_filename=manga.cover_filename,
            authors=manga.authors,
            tags=manga.tags,
            demographic=manga.demographic,
            publication_status=manga.publication_status,
            match_score=score,
        )
        for manga, score in recommendations
    ]

@router.post("/feedback", status_code=status.HTTP_200_OK)
async def submit_recommendation_feedback(
    feedback_in: FeedbackCreate, session: AsyncSession = Depends(get_session)
):
    user = await session.get(User, feedback_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = select(RecommendationFeedback).where(
        RecommendationFeedback.user_id == feedback_in.user_id,
        RecommendationFeedback.manga_id == feedback_in.manga_id,
    )
    res = await session.execute(query)
    existing_fb = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if existing_fb:
        existing_fb.feedback_type = feedback_in.feedback_type
        existing_fb.updated_at = now
    else:
        new_fb = RecommendationFeedback(
            user_id=feedback_in.user_id,
            manga_id=feedback_in.manga_id,
            feedback_type=feedback_in.feedback_type,
            updated_at=now,
        )
        session.add(new_fb)
    await session.commit()
    return {"status": "success", "message": "Feedback recorded successfully"}