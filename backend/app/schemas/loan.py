"""Loan Pydantic v2 schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class LoanCreate(BaseModel):
    bank_name: str = Field(..., max_length=50)
    loan_type: str = Field(..., pattern="^(home|personal|car|education|gold|credit_card)$")
    principal_amount: Decimal = Field(..., gt=0)
    outstanding_principal: Decimal = Field(..., ge=0)
    interest_rate: Decimal = Field(..., ge=0, le=50)
    interest_rate_type: str = Field("floating", pattern="^(floating|fixed|hybrid)$")
    tenure_months: int = Field(..., gt=0, le=600)
    remaining_tenure_months: int = Field(..., gt=0, le=600)
    emi_amount: Decimal = Field(..., gt=0)
    emi_due_date: int | None = Field(None, ge=1, le=28)
    prepayment_penalty_pct: Decimal = Field(Decimal("0"), ge=0)
    foreclosure_charges_pct: Decimal = Field(Decimal("0"), ge=0)
    eligible_80c: bool = False
    eligible_24b: bool = False
    eligible_80e: bool = False
    eligible_80eea: bool = False
    disbursement_date: date | None = None
    source: str = Field("manual", pattern="^(manual|scan|account_aggregator)$")
    source_scan_id: UUID | None = None


class LoanUpdate(BaseModel):
    bank_name: str | None = None
    outstanding_principal: Decimal | None = Field(None, ge=0)
    interest_rate: Decimal | None = Field(None, ge=0, le=50)
    remaining_tenure_months: int | None = Field(None, gt=0)
    emi_amount: Decimal | None = Field(None, gt=0)
    emi_due_date: int | None = Field(None, ge=1, le=28)
    prepayment_penalty_pct: Decimal | None = Field(None, ge=0)
    foreclosure_charges_pct: Decimal | None = Field(None, ge=0)
    eligible_80c: bool | None = None
    eligible_24b: bool | None = None
    eligible_80e: bool | None = None
    eligible_80eea: bool | None = None
    status: str | None = Field(None, pattern="^(active|closed)$")


class LoanResponse(BaseModel):
    id: UUID
    user_id: UUID
    bank_name: str
    loan_type: str
    principal_amount: Decimal
    outstanding_principal: Decimal
    interest_rate: Decimal
    interest_rate_type: str
    tenure_months: int
    remaining_tenure_months: int
    emi_amount: Decimal
    emi_due_date: int | None
    prepayment_penalty_pct: Decimal
    foreclosure_charges_pct: Decimal
    eligible_80c: bool
    eligible_24b: bool
    eligible_80e: bool
    eligible_80eea: bool
    disbursement_date: date | None
    status: str
    source: str
    source_scan_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
