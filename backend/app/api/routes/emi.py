"""EMI calculator routes — public, no auth required."""

from decimal import Decimal
from fastapi import APIRouter

from app.schemas.emi import (
    EMICalculateRequest, EMICalculateResponse,
    ReverseEMIRequest, ReverseEMIResponse,
    AffordabilityRequest, AffordabilityResponse,
)
from app.core.financial_math import (
    calculate_emi, calculate_total_interest, calculate_interest_saved,
    reverse_emi_rate, calculate_affordability,
)

router = APIRouter(prefix="/api/emi", tags=["emi-calculator"])


@router.post("/calculate", response_model=EMICalculateResponse)
async def calculate(req: EMICalculateRequest):
    """Calculate EMI and total interest. Public — no login needed."""
    emi = calculate_emi(req.principal, req.annual_rate, req.tenure_months)
    total_interest = calculate_total_interest(req.principal, req.annual_rate, req.tenure_months)
    total_payment = req.principal + total_interest

    interest_saved = Decimal("0")
    months_saved = 0
    if req.monthly_prepayment > 0:
        interest_saved, months_saved = calculate_interest_saved(
            req.principal, req.annual_rate, req.tenure_months, req.monthly_prepayment
        )

    return EMICalculateResponse(
        emi=emi,
        total_interest=total_interest,
        total_payment=total_payment,
        interest_saved=interest_saved,
        months_saved=months_saved,
    )


@router.post("/reverse-calculate", response_model=ReverseEMIResponse)
async def reverse_calculate(req: ReverseEMIRequest):
    """Find interest rate for a target EMI. Public."""
    rate = reverse_emi_rate(req.principal, req.target_emi, req.tenure_months)
    return ReverseEMIResponse(estimated_rate=rate)


@router.post("/affordability", response_model=AffordabilityResponse)
async def affordability(req: AffordabilityRequest):
    """Calculate max borrowable amount. Public."""
    max_principal = calculate_affordability(req.monthly_emi_budget, req.annual_rate, req.tenure_months)
    total_interest = calculate_total_interest(max_principal, req.annual_rate, req.tenure_months)
    return AffordabilityResponse(
        max_principal=max_principal,
        total_interest=total_interest,
        total_payment=max_principal + total_interest,
    )
