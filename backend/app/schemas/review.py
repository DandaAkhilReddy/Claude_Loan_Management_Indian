"""Pydantic schemas for reviews/feedback."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    review_type: str = Field(..., pattern="^(feedback|testimonial|feature_request)$")
    rating: int | None = Field(None, ge=1, le=5)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=2000)


class ReviewResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_display_name: str | None = None
    review_type: str
    rating: int | None
    title: str
    content: str
    status: str
    admin_response: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewUpdateAdmin(BaseModel):
    status: str | None = None
    admin_response: str | None = None
    is_public: bool | None = None
