from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, JSON

class ListStatus(str, Enum):
    READING = "Reading"
    COMPLETED = "Completed"
    DROPPER = "Dropped"
    PLAN_TO_READ = "Plan to Read"

class FeedbackType(str, Enum):
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    HATE = "HATE"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class MangaCache(SQLModel, table=True):
    manga_id: str = Field(primary_key=True)
    title: str = Field(index=True)
    cover_filename: Optional[str] = None
    authors: List[str] = Field(default=[], sa_column=Column(JSON))
    tags: List[str] = Field(default=[], sa_column=Column(JSON))
    demographic : Optional[str] = None
    publication_status: Optional[str] = None
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class UserMangaList(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    manga_id: str = Field(foreign_key="mangacache.manga_id", index=True)
    status: ListStatus = Field(default=ListStatus.PLAN_TO_READ)
    score: Optional[float] = Field(default=None, ge=1.0, le=10.0)
    last_chapter_read: float = Field(default=0.0)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ChapterLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    manga_id: str = Field(foreign_key="mangacache.manga_id", index=True)
    chapter_number: float = Field(index=True)
    rating: Optional[float] = Field(default=None, ge=1.0, le=10.0)
    notes: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class RecommendationFeedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    manga_id: str = Field(foreign_key="mangacache.manga_id", index=True)
    feedback_type: FeedbackType
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )