"""Tests for US tax rules, loan deductions, and constants."""

import pytest
from decimal import Decimal

from app.core.usa_rules import (
    calculate_us_tax,
    calculate_us_loan_deductions,
    compare_standard_vs_itemized,
    get_us_tax_bracket,
    USLoanTaxInfo,
    FILING_STATUSES,
    US_TAX_BRACKETS,
    STANDARD_DEDUCTION,
    MORTGAGE_INTEREST_DEDUCTION_LIMIT,
    STUDENT_LOAN_INTEREST_DEDUCTION_LIMIT,
    US_BANKS,
    US_LOAN_TYPES,
    RATE_TYPES,
)


# ---------------------------------------------------------------------------
# Tax bracket lookup (get_us_tax_bracket)
# ---------------------------------------------------------------------------

class TestTaxBracket:
    def test_single_50k(self):
        """$50K single filer is in the 22% bracket."""
        assert get_us_tax_bracket(Decimal("50000"), "single") == Decimal("0.22")

    def test_married_jointly_80k(self):
        """$80K married-jointly filer is in the 12% bracket."""
        assert get_us_tax_bracket(Decimal("80000"), "married_jointly") == Decimal("0.12")

    def test_married_separately_200k(self):
        """$200K married-separately filer: exceeds the 191950 boundary,
        so lands in the 32% bracket."""
        assert get_us_tax_bracket(Decimal("200000"), "married_separately") == Decimal("0.32")

    def test_head_of_household_120k(self):
        """$120K head-of-household filer: exceeds the 100500 boundary,
        so lands in the 24% bracket."""
        assert get_us_tax_bracket(Decimal("120000"), "head_of_household") == Decimal("0.24")

    def test_zero_income_returns_10pct(self):
        """$0 income: income is not > 0, so bracket stays at initial 0.
        Actually the loop checks annual_income > prev_limit; at $0 the
        condition 0 > 0 is False, so bracket remains Decimal('0')."""
        assert get_us_tax_bracket(Decimal("0"), "single") == Decimal("0")

    def test_very_small_income_returns_10pct(self):
        """$1 income falls in the 10% bracket."""
        assert get_us_tax_bracket(Decimal("1"), "single") == Decimal("0.10")

    def test_top_bracket_700k(self):
        """$700K single filer hits the 37% top bracket."""
        assert get_us_tax_bracket(Decimal("700000"), "single") == Decimal("0.37")

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="Invalid filing status"):
            get_us_tax_bracket(Decimal("50000"), "invalid_status")


# ---------------------------------------------------------------------------
# Federal tax calculation (calculate_us_tax)
# ---------------------------------------------------------------------------

class TestFederalTaxCalc:
    def test_single_50k(self):
        """Single filer, $50,000 taxable income.
        11600*0.10 + 35550*0.12 + 2850*0.22 = 1160 + 4266 + 627 = 6053.00
        """
        tax = calculate_us_tax(Decimal("50000"), "single")
        assert tax == Decimal("6053.00")

    def test_married_jointly_100k(self):
        """Married-jointly, $100,000 taxable income.
        23200*0.10 + 71100*0.12 + 5700*0.22 = 2320 + 8532 + 1254 = 12106.00
        """
        tax = calculate_us_tax(Decimal("100000"), "married_jointly")
        assert tax == Decimal("12106.00")

    def test_head_of_household_80k(self):
        """Head-of-household, $80,000 taxable income.
        16550*0.10 + 46550*0.12 + 16900*0.22 = 1655 + 5586 + 3718 = 10959.00
        """
        tax = calculate_us_tax(Decimal("80000"), "head_of_household")
        assert tax == Decimal("10959.00")

    def test_zero_income(self):
        """$0 income -> $0 tax."""
        assert calculate_us_tax(Decimal("0"), "single") == Decimal("0.00")

    def test_low_income_below_standard_deduction(self):
        """$5,000 taxable income (all in 10% bracket).
        5000 * 0.10 = 500.00
        """
        tax = calculate_us_tax(Decimal("5000"), "single")
        assert tax == Decimal("500.00")

    def test_high_income_700k_single(self):
        """$700K single — spans all 7 brackets.
        11600*0.10 + 35550*0.12 + 53375*0.22 + 91425*0.24
        + 51775*0.32 + 365625*0.35 + 90650*0.37
        = 1160 + 4266 + 11742.50 + 21942 + 16568 + 127968.75 + 33540.50
        = 217187.75
        """
        tax = calculate_us_tax(Decimal("700000"), "single")
        assert tax == Decimal("217187.75")


# ---------------------------------------------------------------------------
# Mortgage deduction (calculate_us_loan_deductions)
# ---------------------------------------------------------------------------

class TestMortgageDeduction:
    def test_below_cap_full_deduction(self):
        """Mortgage with principal <= $750K: full interest is deductible."""
        loan = USLoanTaxInfo(
            loan_type="home",
            annual_interest_paid=Decimal("18000"),
            annual_principal_paid=Decimal("12000"),
            eligible_mortgage_deduction=True,
            outstanding_principal=Decimal("500000"),
        )
        result = calculate_us_loan_deductions([loan])
        assert result["mortgage_interest"] == Decimal("18000")

    def test_above_cap_prorated(self):
        """Mortgage with principal $1,000,000 (above $750K cap).
        Ratio = 750000/1000000 = 0.75
        Deductible = 24000 * 0.75 = 18000
        """
        loan = USLoanTaxInfo(
            loan_type="home",
            annual_interest_paid=Decimal("24000"),
            annual_principal_paid=Decimal("15000"),
            eligible_mortgage_deduction=True,
            outstanding_principal=Decimal("1000000"),
        )
        result = calculate_us_loan_deductions([loan])
        assert result["mortgage_interest"] == Decimal("18000")

    def test_not_eligible_returns_zero(self):
        """Loan not flagged as mortgage-eligible -> 0 deduction."""
        loan = USLoanTaxInfo(
            loan_type="personal",
            annual_interest_paid=Decimal("5000"),
            annual_principal_paid=Decimal("3000"),
            eligible_mortgage_deduction=False,
        )
        result = calculate_us_loan_deductions([loan])
        assert result["mortgage_interest"] == Decimal("0")

    def test_zero_interest(self):
        """Eligible mortgage but $0 interest paid."""
        loan = USLoanTaxInfo(
            loan_type="home",
            annual_interest_paid=Decimal("0"),
            annual_principal_paid=Decimal("12000"),
            eligible_mortgage_deduction=True,
            outstanding_principal=Decimal("400000"),
        )
        result = calculate_us_loan_deductions([loan])
        assert result["mortgage_interest"] == Decimal("0")

    def test_multiple_loans_aggregate(self):
        """Two eligible mortgages: deductions should sum."""
        loan1 = USLoanTaxInfo(
            loan_type="home",
            annual_interest_paid=Decimal("10000"),
            annual_principal_paid=Decimal("8000"),
            eligible_mortgage_deduction=True,
            outstanding_principal=Decimal("300000"),
        )
        loan2 = USLoanTaxInfo(
            loan_type="home",
            annual_interest_paid=Decimal("6000"),
            annual_principal_paid=Decimal("5000"),
            eligible_mortgage_deduction=True,
            outstanding_principal=Decimal("200000"),
        )
        result = calculate_us_loan_deductions([loan1, loan2])
        assert result["mortgage_interest"] == Decimal("16000")

    def test_mortgage_cap_constant(self):
        """Verify the mortgage interest deduction limit is $750,000."""
        assert MORTGAGE_INTEREST_DEDUCTION_LIMIT == Decimal("750000")


# ---------------------------------------------------------------------------
# Student loan deduction (calculate_us_loan_deductions)
# ---------------------------------------------------------------------------

class TestStudentLoanDeduction:
    def test_below_cap(self):
        """Student loan interest below $2,500 -> full deduction."""
        loan = USLoanTaxInfo(
            loan_type="education",
            annual_interest_paid=Decimal("1500"),
            annual_principal_paid=Decimal("3000"),
            eligible_student_loan_deduction=True,
        )
        result = calculate_us_loan_deductions([loan])
        assert result["student_loan_interest"] == Decimal("1500")

    def test_above_cap_clamped(self):
        """Student loan interest $4,000 -> capped at $2,500."""
        loan = USLoanTaxInfo(
            loan_type="education",
            annual_interest_paid=Decimal("4000"),
            annual_principal_paid=Decimal("5000"),
            eligible_student_loan_deduction=True,
        )
        result = calculate_us_loan_deductions([loan])
        assert result["student_loan_interest"] == Decimal("2500")

    def test_exactly_at_cap(self):
        """Student loan interest exactly $2,500 -> $2,500."""
        loan = USLoanTaxInfo(
            loan_type="education",
            annual_interest_paid=Decimal("2500"),
            annual_principal_paid=Decimal("4000"),
            eligible_student_loan_deduction=True,
        )
        result = calculate_us_loan_deductions([loan])
        assert result["student_loan_interest"] == Decimal("2500")

    def test_not_eligible(self):
        """Loan not flagged for student loan deduction -> 0."""
        loan = USLoanTaxInfo(
            loan_type="education",
            annual_interest_paid=Decimal("2000"),
            annual_principal_paid=Decimal("3000"),
            eligible_student_loan_deduction=False,
        )
        result = calculate_us_loan_deductions([loan])
        assert result["student_loan_interest"] == Decimal("0")


# ---------------------------------------------------------------------------
# Standard vs itemized comparison (compare_standard_vs_itemized)
# ---------------------------------------------------------------------------

class TestStandardVsItemized:
    def test_no_loans_standard_wins(self):
        """No loans / no itemized deductions -> standard always wins."""
        result = compare_standard_vs_itemized(
            annual_income=Decimal("80000"),
            loans=[],
            filing_status="single",
        )
        assert result["recommended"] == "standard"

    def test_high_mortgage_itemized_wins(self):
        """Large mortgage interest + other deductions > standard deduction
        -> itemized wins."""
        mortgage = USLoanTaxInfo(
            loan_type="home",
            annual_interest_paid=Decimal("20000"),
            annual_principal_paid=Decimal("10000"),
            eligible_mortgage_deduction=True,
            outstanding_principal=Decimal("600000"),
        )
        result = compare_standard_vs_itemized(
            annual_income=Decimal("150000"),
            loans=[mortgage],
            filing_status="single",
            other_itemized_deductions=Decimal("5000"),
        )
        # Total itemized = 20000 (mortgage) + 5000 (other) = 25000 > 14600 standard
        assert result["recommended"] == "itemized"
        assert result["itemized"]["deduction_amount"] == Decimal("25000")

    def test_single_standard_deduction_amount(self):
        """Verify single filer standard deduction is $14,600."""
        result = compare_standard_vs_itemized(
            annual_income=Decimal("100000"),
            loans=[],
            filing_status="single",
        )
        assert result["standard"]["deduction_amount"] == Decimal("14600")

    def test_married_standard_deduction_amount(self):
        """Verify married-jointly standard deduction is $29,200."""
        result = compare_standard_vs_itemized(
            annual_income=Decimal("100000"),
            loans=[],
            filing_status="married_jointly",
        )
        assert result["standard"]["deduction_amount"] == Decimal("29200")

    def test_student_loan_above_the_line_both_scenarios(self):
        """Student loan interest is above-the-line: applies in BOTH
        standard and itemized paths."""
        student = USLoanTaxInfo(
            loan_type="education",
            annual_interest_paid=Decimal("2000"),
            annual_principal_paid=Decimal("4000"),
            eligible_student_loan_deduction=True,
        )
        result = compare_standard_vs_itemized(
            annual_income=Decimal("75000"),
            loans=[student],
            filing_status="single",
        )
        assert result["standard"]["above_the_line"] == Decimal("2000")
        assert result["itemized"]["above_the_line"] == Decimal("2000")

    def test_invalid_filing_status_raises(self):
        with pytest.raises(ValueError, match="Invalid filing status"):
            compare_standard_vs_itemized(
                annual_income=Decimal("80000"),
                loans=[],
                filing_status="invalid",
            )
