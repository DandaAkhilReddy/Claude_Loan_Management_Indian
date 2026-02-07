"""EMI calculator Pydantic v2 schemas (public, no auth)."""

from decimal import Decimal
from pydantic import BaseModel, Field


class EMICalculateRequest(BaseModel):
    principal: Decimal = Field(..., gt=0, description="Loan amount in ₹")
    annual_rate: Decimal = Field(..., ge=0, le=50, description="Annual interest rate %")
    tenure_months: int = Field(..., gt=0, le=600, description="Tenure in months")
    monthly_prepayment: Decimal = Field(Decimal("0"), ge=0)


class EMICalculateResponse(BaseModel):
    emi: Decimal
    total_interest: Decimal
    total_payment: Decimal
    interest_saved: Decimal = Decimal("0")
    months_saved: int = 0


class ReverseEMIRequest(BaseModel):
    principal: Decimal = Field(..., gt=0)
    target_emi: Decimal = Field(..., gt=0)
    tenure_months: int = Field(..., gt=0, le=600)


class ReverseEMIResponse(BaseModel):
    estimated_rate: Decimal


class AffordabilityRequest(BaseModel):
    monthly_emi_budget: Decimal = Field(..., gt=0)
    annual_rate: Decimal = Field(..., ge=0, le=50)
    tenure_months: int = Field(..., gt=0, le=600)


class AffordabilityResponse(BaseModel):
    max_principal: Decimal
    total_interest: Decimal
    total_payment: Decimal
