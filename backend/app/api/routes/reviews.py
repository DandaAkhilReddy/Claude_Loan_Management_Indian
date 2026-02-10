"""Review routes — submit feedback, list own reviews, public testimonials."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.models import User
from app.db.repositories.review_repo import ReviewRepository
from app.schemas.review import ReviewCreate, ReviewResponse

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/", response_model=ReviewResponse)
async def submit_review(
    data: ReviewCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a review, feedback, or feature request."""
    repo = ReviewRepository(db)
    review = await repo.create(
        user_id=user.id,
        review_type=data.review_type,
        title=data.title,
        content=data.content,
        rating=data.rating,
    )
    return ReviewResponse(
        **{c.key: getattr(review, c.key) for c in review.__table__.columns},
        user_display_name=user.display_name,
    )


@router.get("/mine", response_model=list[ReviewResponse])
async def my_reviews(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List current user's reviews."""
    repo = ReviewRepository(db)
    reviews = await repo.list_by_user(user.id)
    return [
        ReviewResponse(
            **{c.key: getattr(r, c.key) for c in r.__table__.columns},
            user_display_name=user.display_name,
        )
        for r in reviews
    ]


@router.get("/public", response_model=list[ReviewResponse])
async def public_reviews(
    db: AsyncSession = Depends(get_db),
):
    """List approved public testimonials (no auth required)."""
    repo = ReviewRepository(db)
    reviews = await repo.list_public()
    return [
        ReviewResponse(
            **{c.key: getattr(review, c.key) for c in review.__table__.columns},
            user_display_name=review.user.display_name if review.user else None,
        )
        for review in reviews
    ]
