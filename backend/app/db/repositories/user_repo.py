"""User repository — upsert on Firebase UID."""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, firebase_uid: str, email: str | None = None, phone: str | None = None, display_name: str | None = None) -> User:
        user = await self.get_by_firebase_uid(firebase_uid)
        if user:
            if email is not None:
                user.email = email
            if phone is not None:
                user.phone = phone
            if display_name is not None:
                user.display_name = display_name
        else:
            user = User(
                firebase_uid=firebase_uid,
                email=email,
                phone=phone,
                display_name=display_name,
            )
            self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user_id: uuid.UUID, **kwargs) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await self.session.flush()
        return user

    async def delete(self, user_id: uuid.UUID) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False
        await self.session.delete(user)
        await self.session.flush()
        return True
