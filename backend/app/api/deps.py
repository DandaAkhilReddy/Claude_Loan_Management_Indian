"""API dependencies — auth, database, services."""

import uuid
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.db.repositories.user_repo import UserRepository
from app.services.auth_service import verify_firebase_token


async def get_current_user(
    authorization: str = Header(..., description="Bearer <firebase_token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Verify Firebase token and return/upsert user."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    claims = verify_firebase_token(token)

    if not claims:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    repo = UserRepository(db)
    user = await repo.upsert(
        firebase_uid=claims["uid"],
        email=claims.get("email"),
        phone=claims.get("phone"),
        display_name=claims.get("name"),
    )
    return user


async def get_optional_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Optional auth — returns user or None (for public endpoints)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]
    claims = verify_firebase_token(token)
    if not claims:
        return None

    repo = UserRepository(db)
    return await repo.upsert(
        firebase_uid=claims["uid"],
        email=claims.get("email"),
        phone=claims.get("phone"),
        display_name=claims.get("name"),
    )
