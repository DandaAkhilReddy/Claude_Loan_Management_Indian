"""Tests for Pydantic schema validation."""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.loan import LoanCreate, LoanUpdate
from app.schemas.emi import EMICalculateRequest, ReverseEMIRequest, AffordabilityRequest
from app.schemas.optimizer import OptimizerRequest, WhatIfRequest, SavePlanRequest, TaxImpactRequest
from app.schemas.scanner import ConfirmScanRequest


# ---------------------------------------------------------------------------
# LoanCreate
# ---------------------------------------------------------------------------

class TestLoanCreate:
    @pytest.fixture
    def valid_loan(self):
        return {
            "bank_name": "SBI",
            "loan_type": "home",
            "principal_amount": "5000000",
            "outstanding_principal": "4500000",
            "interest_rate": "8.5",
            "interest_rate_type": "floating",
            "tenure_months": 240,
            "remaining_tenure_months": 220,
            "emi_amount": "43391",
        }

    def test_valid_loan_create(self, valid_loan):
        loan = LoanCreate(**valid_loan)
        assert loan.principal_amount == Decimal("5000000")
        assert loan.loan_type == "home"

    def test_invalid_loan_type(self, valid_loan):
        valid_loan["loan_type"] = "crypto"
        with pytest.raises(ValidationError):
            LoanCreate(**valid_loan)

    def test_negative_principal(self, valid_loan):
        valid_loan["principal_amount"] = "-100"
        with pytest.raises(ValidationError):
            LoanCreate(**valid_loan)

    def test_zero_principal(self, valid_loan):
        valid_loan["principal_amount"] = "0"
        with pytest.raises(ValidationError):
            LoanCreate(**valid_loan)

    def test_rate_above_50(self, valid_loan):
        valid_loan["interest_rate"] = "51"
        with pytest.raises(ValidationError):
            LoanCreate(**valid_loan)

    def test_rate_negative(self, valid_loan):
        valid_loan["interest_rate"] = "-1"
        with pytest.raises(ValidationError):
            LoanCreate(**valid_loan)

    def test_tenure_zero(self, valid_loan):
        valid_loan["tenure_months"] = 0
        with pytest.raises(ValidationError):
            LoanCreate(**valid_loan)

    def test_tenure_exceeds_600(self, valid_loan):
        valid_loan["tenure_months"] = 601
        with pytest.raises(ValidationError):
            LoanCreate(**valid_loan)

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            LoanCreate(bank_name="SBI")

    def test_invalid_rate_type(self, valid_loan):
        valid_loan["interest_rate_type"] = "variable"
        with pytest.raises(ValidationError):
            LoanCreate(**valid_loan)

    def test_invalid_source(self, valid_loan):
        valid_loan["source"] = "unknown_source"
        with pytest.raises(ValidationError):
            LoanCreate(**valid_loan)

    def test_emi_due_date_boundary(self, valid_loan):
        valid_loan["emi_due_date"] = 28
        loan = LoanCreate(**valid_loan)
        assert loan.emi_due_date == 28

    def test_emi_due_date_above_28(self, valid_loan):
        valid_loan["emi_due_date"] = 29
        with pytest.raises(ValidationError):
            LoanCreate(**valid_loan)

    def test_all_loan_types(self, valid_loan):
        for lt in ["home", "personal", "car", "education", "gold", "credit_card"]:
            valid_loan["loan_type"] = lt
            loan = LoanCreate(**valid_loan)
            assert loan.loan_type == lt


# ---------------------------------------------------------------------------
# LoanUpdate
# ---------------------------------------------------------------------------

class TestLoanUpdate:
    def test_partial_update(self):
        update = LoanUpdate(interest_rate=Decimal("9.0"))
        assert update.interest_rate == Decimal("9.0")
        assert update.bank_name is None

    def test_all_none_is_valid(self):
        update = LoanUpdate()
        assert update.bank_name is None

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            LoanUpdate(status="defaulted")


# ---------------------------------------------------------------------------
# EMI schemas
# ---------------------------------------------------------------------------

class TestEMISchemas:
    def test_valid_emi_request(self):
        req = EMICalculateRequest(principal=Decimal("2500000"), annual_rate=Decimal("8.5"), tenure_months=240)
        assert req.monthly_prepayment == Decimal("0")

    def test_emi_negative_principal(self):
        with pytest.raises(ValidationError):
            EMICalculateRequest(principal=Decimal("-100"), annual_rate=Decimal("8.5"), tenure_months=240)

    def test_emi_zero_tenure(self):
        with pytest.raises(ValidationError):
            EMICalculateRequest(principal=Decimal("1000000"), annual_rate=Decimal("8.5"), tenure_months=0)

    def test_reverse_emi_request(self):
        req = ReverseEMIRequest(principal=Decimal("1000000"), target_emi=Decimal("20000"), tenure_months=120)
        assert req.target_emi == Decimal("20000")

    def test_affordability_request(self):
        req = AffordabilityRequest(monthly_emi_budget=Decimal("50000"), annual_rate=Decimal("8.5"), tenure_months=240)
        assert req.monthly_emi_budget == Decimal("50000")


# ---------------------------------------------------------------------------
# Optimizer schemas
# ---------------------------------------------------------------------------

class TestOptimizerSchemas:
    def test_optimizer_request_defaults(self):
        req = OptimizerRequest(loan_ids=["00000000-0000-4000-a000-000000000010"])
        assert req.monthly_extra == Decimal("0")
        assert len(req.strategies) == 4

    def test_optimizer_empty_loan_ids(self):
        with pytest.raises(ValidationError):
            OptimizerRequest(loan_ids=[])

    def test_what_if_request(self):
        req = WhatIfRequest(loan_id="00000000-0000-4000-a000-000000000010")
        assert req.monthly_extra == Decimal("0")
        assert req.lump_sum == Decimal("0")

    def test_save_plan_request(self):
        req = SavePlanRequest(name="My Plan", strategy="avalanche", config={}, results={})
        assert req.name == "My Plan"

    def test_save_plan_name_too_long(self):
        with pytest.raises(ValidationError):
            SavePlanRequest(name="x" * 101, strategy="avalanche", config={}, results={})

    def test_tax_impact_request(self):
        req = TaxImpactRequest(annual_income=Decimal("1200000"))
        assert req.annual_income == Decimal("1200000")

    def test_tax_impact_zero_income(self):
        with pytest.raises(ValidationError):
            TaxImpactRequest(annual_income=Decimal("0"))


# ---------------------------------------------------------------------------
# Scanner schemas
# ---------------------------------------------------------------------------

class TestScannerSchemas:
    def test_confirm_scan_request(self):
        req = ConfirmScanRequest(
            bank_name="SBI",
            loan_type="home",
            principal_amount=5000000.0,
            outstanding_principal=4500000.0,
            interest_rate=8.5,
            tenure_months=240,
            remaining_tenure_months=220,
            emi_amount=43391.0,
        )
        assert req.interest_rate_type == "floating"

    def test_confirm_scan_missing_fields(self):
        with pytest.raises(ValidationError):
            ConfirmScanRequest(bank_name="SBI")
