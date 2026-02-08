"""User data routes — export, delete account."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.db.repositories.loan_repo import LoanRepository
from app.db.repositories.plan_repo import RepaymentPlanRepository
from app.db.repositories.scan_repo import ScanJobRepository
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/user", tags=["user"])


def _serialize_loan(loan) -> dict:
    return {
        "id": str(loan.id),
        "bank_name": loan.bank_name,
        "loan_type": loan.loan_type,
        "principal_amount": float(loan.principal_amount),
        "outstanding_principal": float(loan.outstanding_principal),
        "interest_rate": float(loan.interest_rate),
        "interest_rate_type": loan.interest_rate_type,
        "tenure_months": loan.tenure_months,
        "remaining_tenure_months": loan.remaining_tenure_months,
        "emi_amount": float(loan.emi_amount),
        "emi_due_date": loan.emi_due_date,
        "status": loan.status,
        "eligible_80c": loan.eligible_80c,
        "eligible_24b": loan.eligible_24b,
        "eligible_80e": loan.eligible_80e,
        "eligible_80eea": loan.eligible_80eea,
        "eligible_mortgage_deduction": loan.eligible_mortgage_deduction,
        "eligible_student_loan_deduction": loan.eligible_student_loan_deduction,
        "created_at": loan.created_at.isoformat() if loan.created_at else None,
    }


def _serialize_plan(plan) -> dict:
    return {
        "id": str(plan.id),
        "name": plan.name,
        "strategy": plan.strategy,
        "config": plan.config,
        "results": plan.results,
        "is_active": plan.is_active,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


def _serialize_scan(scan) -> dict:
    return {
        "id": str(scan.id),
        "original_filename": scan.original_filename,
        "status": scan.status,
        "extracted_fields": scan.extracted_fields,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
    }


@router.post("/export-data")
async def export_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all user data as a downloadable JSON file."""
    loan_repo = LoanRepository(db)
    plan_repo = RepaymentPlanRepository(db)
    scan_repo = ScanJobRepository(db)

    loans = await loan_repo.list_by_user(user.id)
    plans = await plan_repo.list_by_user(user.id)
    scans = await scan_repo.list_by_user(user.id)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": {
            "email": user.email,
            "phone": user.phone,
            "display_name": user.display_name,
            "preferred_language": user.preferred_language,
            "country": user.country,
            "tax_regime": user.tax_regime,
            "filing_status": user.filing_status,
            "annual_income": float(user.annual_income) if user.annual_income else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "loans": [_serialize_loan(l) for l in loans],
        "repayment_plans": [_serialize_plan(p) for p in plans],
        "scan_jobs": [_serialize_scan(s) for s in scans],
    }

    return JSONResponse(
        content=export,
        headers={
            "Content-Disposition": f'attachment; filename="loan-data-export-{today}.json"',
        },
    )
