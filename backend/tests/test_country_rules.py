"""Tests for the country-aware rules dispatcher (country_rules.py).

Covers validation, tax brackets, loan deductions, regime/deduction
comparisons, bank constants, and loan type lookups for IN and US.
"""

from decimal import Decimal

import pytest

from app.core.country_rules import (
    SUPPORTED_COUNTRIES,
    compare_tax_options,
    get_banks,
    get_loan_deductions,
    get_loan_types,
    get_tax_bracket,
)
from app.core.indian_rules import LoanTaxInfo
from app.core.usa_rules import USLoanTaxInfo


# ---------------------------------------------------------------------------
# TestValidation
# ---------------------------------------------------------------------------


class TestValidation:
    """Country code validation and normalization."""

    def test_unsupported_country_raises(self):
        """'FR' is not IN or US and must raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported country"):
            get_tax_bracket("FR", Decimal("1000000"))

    def test_supported_countries_constant(self):
        """SUPPORTED_COUNTRIES must be exactly {'IN', 'US'}."""
        assert SUPPORTED_COUNTRIES == {"IN", "US"}

    def test_whitespace_and_case_normalized(self):
        """' in ' (lowercase, padded) should normalize to 'IN' and return a Decimal bracket."""
        result = get_tax_bracket(" in ", Decimal("1200000"))
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# TestGetTaxBracket
# ---------------------------------------------------------------------------


class TestGetTaxBracket:
    """Tax bracket lookups routed to the correct country module."""

    def test_india_old_regime_12l(self):
        """IN old regime: 12,00,000 income falls in the 30% slab."""
        bracket = get_tax_bracket("IN", Decimal("1200000"), regime="old")
        assert bracket == Decimal("0.30")

    def test_india_new_regime_12l(self):
        """IN new regime: 12,00,000 income falls in the 15% slab."""
        bracket = get_tax_bracket("IN", Decimal("1200000"), regime="new")
        assert bracket == Decimal("0.15")

    def test_us_single_110k(self):
        """US single filer at $110,000 falls in the 24% bracket."""
        bracket = get_tax_bracket("US", Decimal("110000"), filing_status="single")
        assert bracket == Decimal("0.24")

    def test_us_married_jointly_50k(self):
        """US married-jointly filer at $50,000 falls in the 12% bracket."""
        bracket = get_tax_bracket(
            "US", Decimal("50000"), filing_status="married_jointly"
        )
        assert bracket == Decimal("0.12")


# ---------------------------------------------------------------------------
# TestGetLoanDeductions
# ---------------------------------------------------------------------------


class TestGetLoanDeductions:
    """Loan deduction calculations routed by country."""

    def test_india_home_loan_old_regime_keys(self):
        """IN old regime home loan returns dict with 80C, 24b, 80e, 80eea, total."""
        loans = [
            LoanTaxInfo(
                loan_type="home",
                annual_interest_paid=Decimal("400000"),
                annual_principal_paid=Decimal("120000"),
                eligible_80c=True,
                eligible_24b=True,
            )
        ]
        result = get_loan_deductions("IN", loans, regime="old")

        assert "80c" in result
        assert "24b" in result
        assert "total" in result
        # 80C capped at 1.5L; principal is 1.2L so deduction = 1.2L
        assert result["80c"] == Decimal("120000")
        # 24b self-occupied capped at 2L; interest is 4L so capped
        assert result["24b"] == Decimal("200000")
        # total should be sum of all sections
        assert result["total"] == result["80c"] + result["24b"] + result["80e"] + result["80eea"]

    def test_india_new_regime_returns_zeros(self):
        """IN new regime returns all-zero deductions (very limited benefits)."""
        loans = [
            LoanTaxInfo(
                loan_type="home",
                annual_interest_paid=Decimal("400000"),
                annual_principal_paid=Decimal("120000"),
                eligible_80c=True,
                eligible_24b=True,
            )
        ]
        result = get_loan_deductions("IN", loans, regime="new")
        assert result["total"] == Decimal("0")

    def test_us_mortgage_deduction_keys(self):
        """US mortgage deduction returns dict with mortgage_interest and totals."""
        loans = [
            USLoanTaxInfo(
                loan_type="home",
                annual_interest_paid=Decimal("18000"),
                annual_principal_paid=Decimal("12000"),
                eligible_mortgage_deduction=True,
                outstanding_principal=Decimal("400000"),
            )
        ]
        result = get_loan_deductions("US", loans, filing_status="single")

        assert "mortgage_interest" in result
        assert "total_itemizable" in result
        assert "total_above_the_line" in result
        # Principal under $750K cap, so full interest is deductible
        assert result["mortgage_interest"] == Decimal("18000")
        assert result["total_itemizable"] == Decimal("18000")

    def test_us_student_loan_deduction(self):
        """US student loan interest is capped at $2,500 (above-the-line)."""
        loans = [
            USLoanTaxInfo(
                loan_type="education",
                annual_interest_paid=Decimal("5000"),
                annual_principal_paid=Decimal("8000"),
                eligible_student_loan_deduction=True,
            )
        ]
        result = get_loan_deductions("US", loans, filing_status="single")

        assert result["student_loan_interest"] == Decimal("2500")
        assert result["total_above_the_line"] == Decimal("2500")


# ---------------------------------------------------------------------------
# TestCompareTaxOptions
# ---------------------------------------------------------------------------


class TestCompareTaxOptions:
    """Tax regime / deduction strategy comparison."""

    def test_india_returns_regime_keys(self):
        """IN comparison returns old_regime, new_regime, recommended, savings."""
        loans = [
            LoanTaxInfo(
                loan_type="home",
                annual_interest_paid=Decimal("300000"),
                annual_principal_paid=Decimal("100000"),
                eligible_80c=True,
                eligible_24b=True,
            )
        ]
        result = compare_tax_options("IN", Decimal("1200000"), loans)

        assert "old_regime" in result
        assert "new_regime" in result
        assert "recommended" in result
        assert "savings" in result
        assert result["recommended"] in ("old", "new")

    def test_us_returns_standard_itemized_keys(self):
        """US comparison returns standard, itemized, recommended, savings."""
        loans = [
            USLoanTaxInfo(
                loan_type="home",
                annual_interest_paid=Decimal("18000"),
                annual_principal_paid=Decimal("12000"),
                eligible_mortgage_deduction=True,
                outstanding_principal=Decimal("400000"),
            )
        ]
        result = compare_tax_options(
            "US", Decimal("110000"), loans, filing_status="single"
        )

        assert "standard" in result
        assert "itemized" in result
        assert "recommended" in result
        assert "savings" in result
        assert result["recommended"] in ("standard", "itemized")

    def test_us_other_itemized_forwarded(self):
        """other_itemized_deductions kwarg is forwarded and affects the result."""
        loans = [
            USLoanTaxInfo(
                loan_type="home",
                annual_interest_paid=Decimal("8000"),
                annual_principal_paid=Decimal("6000"),
                eligible_mortgage_deduction=True,
                outstanding_principal=Decimal("300000"),
            )
        ]
        # With large other itemized deductions, itemized total should be higher
        result = compare_tax_options(
            "US",
            Decimal("150000"),
            loans,
            filing_status="single",
            other_itemized_deductions=Decimal("20000"),
        )

        # Itemized deduction_amount should include the $20K in other deductions
        assert result["itemized"]["other_deductions"] == Decimal("20000")
        total_itemized = result["itemized"]["deduction_amount"]
        # 8000 mortgage + 20000 other = 28000 > 14600 standard
        assert total_itemized == Decimal("28000")


# ---------------------------------------------------------------------------
# TestGetBanks
# ---------------------------------------------------------------------------


class TestGetBanks:
    """Bank constant lookups."""

    def test_india_banks_include_sbi(self):
        """Indian bank list must include SBI."""
        banks = get_banks("IN")
        assert "SBI" in banks
        assert banks["SBI"]["full_name"] == "State Bank of India"

    def test_us_banks_include_chase(self):
        """US bank list must include CHASE."""
        banks = get_banks("US")
        assert "CHASE" in banks
        assert banks["CHASE"]["full_name"] == "JPMorgan Chase"


# ---------------------------------------------------------------------------
# TestGetLoanTypes
# ---------------------------------------------------------------------------


class TestGetLoanTypes:
    """Loan type lookups by country."""

    def test_india_types_include_gold(self):
        """Indian loan types must include 'gold'."""
        types = get_loan_types("IN")
        assert "gold" in types

    def test_us_types_exclude_gold_include_business(self):
        """US loan types must exclude 'gold' but include 'business'."""
        types = get_loan_types("US")
        assert "gold" not in types
        assert "business" in types
