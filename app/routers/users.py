from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.models import User
from app.schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate, session: AsyncSession = Depends(get_session)
):
    query = select(User).where(User.username == user_in.username)
    res = await session.execute(query)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=400, details="Username is already registered"
        )

    user = User(username=user_in.username)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@router.get("/{user_id}", response_model=UserRead)
async def get_user(
        user_id: int, session: AsyncSession = Depends(get_session)
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user