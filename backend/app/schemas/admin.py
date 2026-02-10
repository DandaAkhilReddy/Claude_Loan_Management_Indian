"""Pydantic schemas for admin dashboard."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class AdminStatsResponse(BaseModel):
    user_count: int
    new_users_7d: int
    new_users_30d: int
    total_loans: int
    loans_by_type: dict[str, int]
    total_scans: int
    scans_today: int
    scan_success_rate: float
    total_reviews: int


class UsageSummaryResponse(BaseModel):
    total_cost_30d: float
    total_calls_30d: int
    by_service: dict[str, dict]
    daily_costs: list[dict]


class AdminUserRow(BaseModel):
    id: UUID
    email: str | None
    display_name: str | None
    created_at: datetime
    loan_count: int

    model_config = {"from_attributes": True}
