"""Admin routes — dashboard stats, user list, usage, review management."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, cast, Date, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.db.models import User, Loan, ScanJob, Review
from app.db.repositories.review_repo import ReviewRepository
from app.db.repositories.usage_repo import UsageLogRepository
from app.schemas.admin import AdminStatsResponse, UsageSummaryResponse, AdminUserRow
from app.schemas.review import ReviewResponse, ReviewUpdateAdmin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard metrics: users, loans, scans, reviews."""
    now = datetime.now(timezone.utc)

    # User counts
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    new_7d = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= now - timedelta(days=7))
    )).scalar() or 0
    new_30d = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= now - timedelta(days=30))
    )).scalar() or 0

    # Loan counts
    total_loans = (await db.execute(select(func.count(Loan.id)))).scalar() or 0
    loan_type_rows = (await db.execute(
        select(Loan.loan_type, func.count(Loan.id)).group_by(Loan.loan_type)
    )).all()
    loans_by_type = {row[0]: row[1] for row in loan_type_rows}

    # Scan counts
    total_scans = (await db.execute(select(func.count(ScanJob.id)))).scalar() or 0
    scans_today = (await db.execute(
        select(func.count(ScanJob.id)).where(
            cast(ScanJob.created_at, Date) == now.date()
        )
    )).scalar() or 0
    scans_completed = (await db.execute(
        select(func.count(ScanJob.id)).where(ScanJob.status == "completed")
    )).scalar() or 0
    scan_success_rate = round(scans_completed / total_scans * 100, 1) if total_scans > 0 else 0.0

    # Review count
    total_reviews = (await db.execute(select(func.count(Review.id)))).scalar() or 0

    return AdminStatsResponse(
        user_count=user_count,
        new_users_7d=new_7d,
        new_users_30d=new_30d,
        total_loans=total_loans,
        loans_by_type=loans_by_type,
        total_scans=total_scans,
        scans_today=scans_today,
        scan_success_rate=scan_success_rate,
        total_reviews=total_reviews,
    )


@router.get("/users", response_model=list[AdminUserRow])
async def list_users(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users with loan count."""
    result = await db.execute(
        select(
            User.id, User.email, User.display_name, User.created_at,
            func.count(Loan.id).label("loan_count"),
        )
        .outerjoin(Loan, and_(Loan.user_id == User.id, Loan.status == "active"))
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )
    rows = result.all()
    return [
        AdminUserRow(
            id=r.id, email=r.email, display_name=r.display_name,
            created_at=r.created_at, loan_count=r.loan_count,
        )
        for r in rows
    ]


@router.get("/usage", response_model=UsageSummaryResponse)
async def get_usage(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """API usage summary and daily breakdown (30 days)."""
    repo = UsageLogRepository(db)
    summary = await repo.get_summary(days=30)
    daily = await repo.get_daily_breakdown(days=30)
    return UsageSummaryResponse(
        total_cost_30d=summary["total_cost"],
        total_calls_30d=summary["total_calls"],
        by_service=summary["by_service"],
        daily_costs=daily,
    )


@router.get("/reviews", response_model=list[ReviewResponse])
async def list_reviews(
    review_type: str | None = Query(None),
    status: str | None = Query(None),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all reviews (filterable)."""
    repo = ReviewRepository(db)
    reviews = await repo.list_all(review_type=review_type, status=status)
    return [
        ReviewResponse(
            **{c.key: getattr(r, c.key) for c in r.__table__.columns},
            user_display_name=r.user.display_name if r.user else None,
        )
        for r in reviews
    ]


@router.put("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: UUID,
    data: ReviewUpdateAdmin,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update review status/response (admin)."""
    repo = ReviewRepository(db)
    review = await repo.update_status(
        review_id,
        status=data.status,
        admin_response=data.admin_response,
        is_public=data.is_public,
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewResponse(
        **{c.key: getattr(review, c.key) for c in review.__table__.columns},
        user_display_name=review.user.display_name if review.user else None,
    )


@router.delete("/reviews/{review_id}")
async def delete_review(
    review_id: UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a review (admin)."""
    repo = ReviewRepository(db)
    if not await repo.delete(review_id):
        raise HTTPException(status_code=404, detail="Review not found")
    return {"detail": "Review deleted"}
