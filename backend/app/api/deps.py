"""API dependencies — auth paused for testing."""

import uuid
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.db.repositories.user_repo import UserRepository

# ── Auth paused: upsert a dev user on every request (no token check) ──

DEV_UID = "dev-admin"
DEV_EMAIL = "admin@test.com"
DEV_NAME = "Admin"


async def get_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Auth paused — return/upsert a dev user without verifying tokens."""
    repo = UserRepository(db)
    user = await repo.upsert(
        firebase_uid=DEV_UID,
        email=DEV_EMAIL,
        phone=None,
        display_name=DEV_NAME,
    )
    return user


async def get_optional_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Auth paused — always returns the dev user."""
    return await get_current_user(authorization, db)
