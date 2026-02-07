"""Loan CRUD routes with user scoping."""

from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.models import User
from app.db.repositories.loan_repo import LoanRepository
from app.schemas.loan import LoanCreate, LoanUpdate, LoanResponse
from app.core.financial_math import generate_amortization

router = APIRouter(prefix="/api/loans", tags=["loans"])


@router.get("", response_model=list[LoanResponse])
async def list_loans(
    loan_type: str | None = Query(None),
    status: str | None = Query(None),
    bank_name: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's loans with optional filters."""
    repo = LoanRepository(db)
    loans = await repo.list_by_user(user.id, loan_type=loan_type, status=status, bank_name=bank_name)
    return [LoanResponse.model_validate(loan) for loan in loans]


@router.post("", response_model=LoanResponse, status_code=201)
async def create_loan(
    data: LoanCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new loan."""
    repo = LoanRepository(db)
    loan = await repo.create(user_id=user.id, **data.model_dump())
    return LoanResponse.model_validate(loan)


@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get loan detail."""
    repo = LoanRepository(db)
    loan = await repo.get_by_id(loan_id, user.id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return LoanResponse.model_validate(loan)


@router.put("/{loan_id}", response_model=LoanResponse)
async def update_loan(
    loan_id: UUID,
    data: LoanUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a loan."""
    repo = LoanRepository(db)
    updates = data.model_dump(exclude_none=True)
    loan = await repo.update(loan_id, user.id, **updates)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return LoanResponse.model_validate(loan)


@router.delete("/{loan_id}")
async def delete_loan(
    loan_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a loan permanently."""
    repo = LoanRepository(db)
    deleted = await repo.delete(loan_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Loan not found")
    return {"message": "Loan deleted"}


@router.get("/{loan_id}/amortization")
async def get_amortization(
    loan_id: UUID,
    prepayment: float = Query(0, ge=0, description="Monthly prepayment amount"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get amortization schedule for a loan."""
    repo = LoanRepository(db)
    loan = await repo.get_by_id(loan_id, user.id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    schedule = generate_amortization(
        principal=Decimal(str(loan.outstanding_principal)),
        annual_rate=Decimal(str(loan.interest_rate)),
        tenure_months=loan.remaining_tenure_months,
        monthly_prepayment=Decimal(str(prepayment)),
    )

    return {
        "loan_id": str(loan.id),
        "schedule": [
            {
                "month": entry.month,
                "emi": float(entry.emi),
                "principal": float(entry.principal),
                "interest": float(entry.interest),
                "balance": float(entry.balance),
                "prepayment": float(entry.prepayment),
                "cumulative_interest": float(entry.cumulative_interest),
            }
            for entry in schedule
        ],
        "total_months": len(schedule),
        "total_interest": float(schedule[-1].cumulative_interest) if schedule else 0,
    }
