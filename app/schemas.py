from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models import ListStatus, FeedbackType

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserRead(BaseModel):
    id: int
    username: str
    created_at: datetime

class MangaRead(BaseModel):
    manga_id: str
    title: str
    cover_filename: Optional[str] = None
    authors: List[str]
    tags: List[str]
    demographic: Optional[str] = None
    publication_status: Optional[str] = None
    updated_at: Optional[datetime] = None

class ListEntryCreateUpdate(BaseModel):
    user_id: int
    manga_id: str
    status: ListStatus
    score: Optional[float] = Field(default=None, ge=1.0, le=10.0)
    last_chapter_read: float = Field(default=0.0, ge=0.0)


class ListEntryRead(BaseModel):
    id: int
    user_id: int
    manga_id: str
    status: ListStatus
    score: Optional[float]
    last_chapter_read: float
    updated_at: datetime


class ChapterLogCreate(BaseModel):
    user_id: int
    manga_id: str
    chapter_number: float = Field(..., ge=0.0)
    rating: Optional[float] = Field(default=None, ge=1.0, le=10.0)
    notes: Optional[str] = None


class ChapterLogRead(BaseModel):
    id: int
    user_id: int
    manga_id: str
    chapter_number: float
    rating: Optional[float]
    notes: Optional[str]
    created_at: datetime