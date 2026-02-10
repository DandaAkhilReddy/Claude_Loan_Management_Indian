"""Review repository — CRUD for feedback, testimonials, and feature requests."""

import uuid
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Review


class ReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: uuid.UUID, review_type: str, title: str, content: str, rating: int | None = None) -> Review:
        review = Review(
            user_id=user_id,
            review_type=review_type,
            title=title,
            content=content,
            rating=rating,
            status="pending" if review_type == "testimonial" else "new",
        )
        self.session.add(review)
        await self.session.flush()
        return review

    async def list_by_user(self, user_id: uuid.UUID) -> list[Review]:
        result = await self.session.execute(
            select(Review).where(Review.user_id == user_id).order_by(Review.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(
        self,
        review_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Review]:
        query = select(Review)
        if review_type:
            query = query.where(Review.review_type == review_type)
        if status:
            query = query.where(Review.status == status)
        query = query.order_by(Review.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_public(self) -> list[Review]:
        result = await self.session.execute(
            select(Review).where(
                and_(Review.is_public == True, Review.status == "approved")
            ).order_by(Review.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, review_id: uuid.UUID) -> Review | None:
        result = await self.session.execute(select(Review).where(Review.id == review_id))
        return result.scalar_one_or_none()

    async def update_status(
        self,
        review_id: uuid.UUID,
        status: str,
        admin_response: str | None = None,
        is_public: bool | None = None,
    ) -> Review | None:
        review = await self.get_by_id(review_id)
        if not review:
            return None
        review.status = status
        if admin_response is not None:
            review.admin_response = admin_response
        if is_public is not None:
            review.is_public = is_public
        await self.session.flush()
        return review

    async def delete(self, review_id: uuid.UUID) -> bool:
        review = await self.get_by_id(review_id)
        if not review:
            return False
        await self.session.delete(review)
        await self.session.flush()
        return True

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count(Review.id)))
        return result.scalar() or 0
