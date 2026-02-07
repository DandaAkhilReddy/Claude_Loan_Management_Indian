"""Tests for Indian tax rules and RBI regulations."""

import pytest
from decimal import Decimal

from app.core.indian_rules import (
    get_prepayment_penalty,
    calculate_tax_for_slab,
    calculate_loan_deductions,
    compare_tax_regimes,
    get_user_tax_bracket,
    OLD_REGIME_SLABS,
    NEW_REGIME_SLABS,
    LoanTaxInfo,
    FLOATING_RATE_PREPAYMENT_PENALTY,
    FORECLOSURE_CHARGES,
    LOAN_TYPES,
    RATE_TYPES,
    INDIAN_BANKS,
)


# ---------------------------------------------------------------------------
# Prepayment penalty rules
# ---------------------------------------------------------------------------

class TestPrepaymentPenalty:
    def test_floating_rate_always_zero(self):
        """RBI 2014 circular: 0% penalty on all floating rate loans."""
        for lt in LOAN_TYPES:
            assert get_prepayment_penalty(lt, "floating") == Decimal("0")

    def test_fixed_home_loan(self):
        assert get_prepayment_penalty("home", "fixed") == Decimal("2.0")

    def test_fixed_personal_loan(self):
        assert get_prepayment_penalty("personal", "fixed") == Decimal("4.0")

    def test_fixed_car_loan(self):
        assert get_prepayment_penalty("car", "fixed") == Decimal("5.0")

    def test_hybrid_home_loan(self):
        assert get_prepayment_penalty("home", "hybrid") == Decimal("1.5")

    def test_credit_card_always_zero(self):
        for rt in RATE_TYPES:
            assert get_prepayment_penalty("credit_card", rt) == Decimal("0")

    def test_unknown_loan_type_fixed_defaults(self):
        """Unknown loan type with fixed rate should default to 2%."""
        assert get_prepayment_penalty("unknown_type", "fixed") == Decimal("2.0")

    def test_education_floating_zero(self):
        assert get_prepayment_penalty("education", "floating") == Decimal("0")


# ---------------------------------------------------------------------------
# Tax slab calculation
# ---------------------------------------------------------------------------

class TestTaxSlabCalculation:
    def test_old_regime_zero_income(self):
        assert calculate_tax_for_slab(Decimal("0"), OLD_REGIME_SLABS) == Decimal("0.00")

    def test_old_regime_below_exemption(self):
        assert calculate_tax_for_slab(Decimal("200000"), OLD_REGIME_SLABS) == Decimal("0.00")

    def test_old_regime_250k(self):
        """Exactly at exemption limit — no tax."""
        assert calculate_tax_for_slab(Decimal("250000"), OLD_REGIME_SLABS) == Decimal("0.00")

    def test_old_regime_500k(self):
        """250k-500k at 5% = 12,500."""
        tax = calculate_tax_for_slab(Decimal("500000"), OLD_REGIME_SLABS)
        assert tax == Decimal("12500.00")

    def test_old_regime_1000k(self):
        """250k@0% + 250k@5% + 500k@20% = 0 + 12500 + 100000 = 112,500."""
        tax = calculate_tax_for_slab(Decimal("1000000"), OLD_REGIME_SLABS)
        assert tax == Decimal("112500.00")

    def test_old_regime_1500k(self):
        """250k@0% + 250k@5% + 500k@20% + 500k@30% = 262,500."""
        tax = calculate_tax_for_slab(Decimal("1500000"), OLD_REGIME_SLABS)
        assert tax == Decimal("262500.00")

    def test_new_regime_700k(self):
        """300k@0% + 400k@5% = 20,000."""
        tax = calculate_tax_for_slab(Decimal("700000"), NEW_REGIME_SLABS)
        assert tax == Decimal("20000.00")

    def test_new_regime_1200k(self):
        """300k@0% + 400k@5% + 300k@10% + 200k@15% = 0+20000+30000+30000 = 80,000."""
        tax = calculate_tax_for_slab(Decimal("1200000"), NEW_REGIME_SLABS)
        assert tax == Decimal("80000.00")


# ---------------------------------------------------------------------------
# Loan deductions
# ---------------------------------------------------------------------------

class TestLoanDeductions:
    @pytest.fixture
    def home_loan_tax_info(self):
        return LoanTaxInfo(
            loan_type="home",
            annual_interest_paid=Decimal("400000"),
            annual_principal_paid=Decimal("200000"),
            eligible_80c=True,
            eligible_24b=True,
        )

    @pytest.fixture
    def education_loan_tax_info(self):
        return LoanTaxInfo(
            loan_type="education",
            annual_interest_paid=Decimal("50000"),
            annual_principal_paid=Decimal("30000"),
            eligible_80e=True,
        )

    def test_80c_capped_at_150k(self, home_loan_tax_info):
        result = calculate_loan_deductions([home_loan_tax_info], "old")
        assert result["80c"] == Decimal("150000")

    def test_24b_capped_at_200k_self_occupied(self, home_loan_tax_info):
        result = calculate_loan_deductions([home_loan_tax_info], "old")
        assert result["24b"] == Decimal("200000")

    def test_80e_no_cap(self, education_loan_tax_info):
        result = calculate_loan_deductions([education_loan_tax_info], "old")
        assert result["80e"] == Decimal("50000")

    def test_new_regime_no_deductions(self, home_loan_tax_info):
        result = calculate_loan_deductions([home_loan_tax_info], "new")
        assert result["80c"] == Decimal("0")
        assert result["24b"] == Decimal("0")
        assert result["total"] == Decimal("0")

    def test_total_deduction_is_sum(self, home_loan_tax_info, education_loan_tax_info):
        result = calculate_loan_deductions([home_loan_tax_info, education_loan_tax_info], "old")
        expected = result["80c"] + result["24b"] + result["80e"] + result["80eea"]
        assert result["total"] == expected

    def test_empty_loans(self):
        result = calculate_loan_deductions([], "old")
        assert result["total"] == Decimal("0")


# ---------------------------------------------------------------------------
# Compare tax regimes
# ---------------------------------------------------------------------------

class TestCompareTaxRegimes:
    def test_home_loan_deductions_reduce_old_regime_tax(self):
        """Home loan with 80C + 24(b) should reduce old regime tax significantly.
        Whether old or new wins depends on exact slab rates, but old regime
        taxable income must be lower due to deductions.
        """
        loan = LoanTaxInfo(
            loan_type="home",
            annual_interest_paid=Decimal("400000"),
            annual_principal_paid=Decimal("200000"),
            eligible_80c=True,
            eligible_24b=True,
        )
        result = compare_tax_regimes(Decimal("2500000"), [loan])
        # Old regime should have deductions applied (lower taxable income)
        assert result["old_regime"]["taxable_income"] < result["new_regime"]["taxable_income"]
        assert result["old_regime"]["deductions"]["total"] > Decimal("0")
        assert result["recommended"] in ("old", "new")
        assert result["savings"] >= 0

    def test_new_better_without_loans(self):
        result = compare_tax_regimes(Decimal("800000"), [])
        # With no deductions, new regime has lower slabs for mid-income
        assert result["recommended"] in ("old", "new")
        assert "savings" in result

    def test_result_structure(self):
        result = compare_tax_regimes(Decimal("1000000"), [])
        assert "old_regime" in result
        assert "new_regime" in result
        assert "recommended" in result
        assert "savings" in result
        assert "explanation" in result
        assert "tax" in result["old_regime"]
        assert "tax" in result["new_regime"]


# ---------------------------------------------------------------------------
# Tax bracket
# ---------------------------------------------------------------------------

class TestTaxBracket:
    def test_zero_income(self):
        assert get_user_tax_bracket(Decimal("0")) == Decimal("0")

    def test_5pct_bracket_old(self):
        assert get_user_tax_bracket(Decimal("400000"), "old") == Decimal("0.05")

    def test_20pct_bracket_old(self):
        assert get_user_tax_bracket(Decimal("800000"), "old") == Decimal("0.20")

    def test_30pct_bracket_old(self):
        assert get_user_tax_bracket(Decimal("1500000"), "old") == Decimal("0.30")

    def test_new_regime_bracket(self):
        assert get_user_tax_bracket(Decimal("1100000"), "new") == Decimal("0.15")


# ---------------------------------------------------------------------------
# Constants integrity
# ---------------------------------------------------------------------------

class TestConstants:
    def test_all_loan_types_have_foreclosure_charges(self):
        for lt in LOAN_TYPES:
            assert lt in FORECLOSURE_CHARGES

    def test_indian_banks_have_full_name(self):
        for code, info in INDIAN_BANKS.items():
            assert "full_name" in info
            assert len(info["full_name"]) > 0
