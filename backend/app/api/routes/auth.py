"""Auth routes — token verification and profile management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.models import User
from app.db.repositories.user_repo import UserRepository

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserProfileResponse(BaseModel):
    id: str
    email: str | None
    phone: str | None
    display_name: str | None
    preferred_language: str
    tax_regime: str
    annual_income: float | None

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    preferred_language: str | None = None
    tax_regime: str | None = None
    annual_income: float | None = None


@router.post("/verify-token")
async def verify_token(user: User = Depends(get_current_user)):
    """Verify Firebase token and return user profile."""
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        phone=user.phone,
        display_name=user.display_name,
        preferred_language=user.preferred_language,
        tax_regime=user.tax_regime,
        annual_income=float(user.annual_income) if user.annual_income else None,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        phone=user.phone,
        display_name=user.display_name,
        preferred_language=user.preferred_language,
        tax_regime=user.tax_regime,
        annual_income=float(user.annual_income) if user.annual_income else None,
    )


@router.put("/me", response_model=UserProfileResponse)
async def update_profile(
    update: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile."""
    repo = UserRepository(db)
    updates = update.model_dump(exclude_none=True)
    if updates:
        user = await repo.update(user.id, **updates)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        phone=user.phone,
        display_name=user.display_name,
        preferred_language=user.preferred_language,
        tax_regime=user.tax_regime,
        annual_income=float(user.annual_income) if user.annual_income else None,
    )
