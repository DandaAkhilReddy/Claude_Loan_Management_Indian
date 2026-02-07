"""Comprehensive unit tests for the financial math engine.

Validates EMI calculation, amortization schedules, interest savings,
reverse-EMI solvers, and affordability against known Indian bank benchmarks.

All monetary assertions use Decimal for paisa-level precision.
"""

import pytest
from decimal import Decimal

from app.core.financial_math import (
    calculate_emi,
    generate_amortization,
    calculate_total_interest,
    calculate_interest_saved,
    reverse_emi_rate,
    reverse_emi_tenure,
    calculate_affordability,
    AmortizationEntry,
    PAISA,
)


# =====================================================================
# EMI CALCULATION TESTS
# =====================================================================

class TestCalculateEMI:
    """Tests for the core EMI formula: P * r * (1+r)^n / ((1+r)^n - 1)."""

    def test_sbi_benchmark_home_loan(self):
        """SBI benchmark: 50,00,000 at 8.5% for 240 months = ~43,391."""
        emi = calculate_emi(
            principal=Decimal("5000000"),
            annual_rate=Decimal("8.5"),
            tenure_months=240,
        )
        # Allow +/- 1 rupee tolerance for rounding differences
        assert abs(emi - Decimal("43391")) <= Decimal("1"), (
            f"SBI benchmark EMI expected ~43,391 but got {emi}"
        )

    def test_hdfc_benchmark_personal_loan(self):
        """HDFC benchmark: 10,00,000 at 12% for 60 months = ~22,244."""
        emi = calculate_emi(
            principal=Decimal("1000000"),
            annual_rate=Decimal("12"),
            tenure_months=60,
        )
        assert abs(emi - Decimal("22244")) <= Decimal("1"), (
            f"HDFC benchmark EMI expected ~22,244 but got {emi}"
        )

    def test_zero_rate_returns_simple_division(self):
        """0% rate means EMI = principal / tenure (no interest)."""
        emi = calculate_emi(
            principal=Decimal("1200000"),
            annual_rate=Decimal("0"),
            tenure_months=120,
        )
        expected = Decimal("1200000") / 120
        assert emi == expected.quantize(PAISA), (
            f"0% rate EMI should be {expected} but got {emi}"
        )

    def test_zero_rate_non_even_division(self):
        """0% rate with non-evenly-divisible principal rounds to paisa."""
        emi = calculate_emi(
            principal=Decimal("1000000"),
            annual_rate=Decimal("0"),
            tenure_months=7,
        )
        expected = (Decimal("1000000") / 7).quantize(PAISA)
        assert emi == expected

    def test_zero_principal_returns_zero(self):
        """Zero principal should return zero EMI."""
        emi = calculate_emi(Decimal("0"), Decimal("8.5"), 240)
        assert emi == Decimal("0")

    def test_negative_principal_returns_zero(self):
        """Negative principal should return zero EMI."""
        emi = calculate_emi(Decimal("-100000"), Decimal("8.5"), 240)
        assert emi == Decimal("0")

    def test_zero_tenure_returns_zero(self):
        """Zero tenure should return zero EMI."""
        emi = calculate_emi(Decimal("1000000"), Decimal("8.5"), 0)
        assert emi == Decimal("0")

    def test_negative_tenure_returns_zero(self):
        """Negative tenure should return zero EMI."""
        emi = calculate_emi(Decimal("1000000"), Decimal("8.5"), -12)
        assert emi == Decimal("0")

    def test_very_high_rate(self):
        """Very high interest rate (36%) still produces a finite EMI."""
        emi = calculate_emi(
            principal=Decimal("100000"),
            annual_rate=Decimal("36"),
            tenure_months=12,
        )
        assert emi > Decimal("0")
        # Total paid should be significantly more than principal at 36%
        total_paid = emi * 12
        assert total_paid > Decimal("100000")

    def test_one_month_tenure(self):
        """Single month tenure: EMI should be principal + one month interest."""
        principal = Decimal("100000")
        rate = Decimal("12")
        emi = calculate_emi(principal, rate, 1)
        # For 1 month: EMI = P * (1 + r) essentially
        monthly_rate = rate / Decimal("1200")
        expected = principal * (1 + monthly_rate)
        assert abs(emi - expected.quantize(PAISA)) <= Decimal("0.01")

    def test_emi_is_positive_decimal(self):
        """EMI must always be a positive Decimal with at most 2 decimal places."""
        emi = calculate_emi(Decimal("500000"), Decimal("9"), 120)
        assert isinstance(emi, Decimal)
        assert emi > Decimal("0")
        # Check that it is quantized to paisa
        assert emi == emi.quantize(PAISA)

    def test_higher_rate_produces_higher_emi(self):
        """For same principal/tenure, a higher rate must produce a higher EMI."""
        emi_low = calculate_emi(Decimal("1000000"), Decimal("8"), 120)
        emi_high = calculate_emi(Decimal("1000000"), Decimal("12"), 120)
        assert emi_high > emi_low

    def test_longer_tenure_produces_lower_emi(self):
        """For same principal/rate, a longer tenure must produce a lower EMI."""
        emi_short = calculate_emi(Decimal("1000000"), Decimal("9"), 60)
        emi_long = calculate_emi(Decimal("1000000"), Decimal("9"), 240)
        assert emi_long < emi_short

    def test_small_loan_amount(self):
        """Small loan of 10,000 at 10% for 12 months should work correctly."""
        emi = calculate_emi(Decimal("10000"), Decimal("10"), 12)
        # Should be roughly 879
        assert Decimal("870") < emi < Decimal("890")


# =====================================================================
# AMORTIZATION SCHEDULE TESTS
# =====================================================================

class TestGenerateAmortization:
    """Tests for full amortization schedule generation."""

    def test_sum_of_principal_payments_equals_original(self):
        """Sum of all principal payments must equal the original principal (+-1 rounding)."""
        principal = Decimal("5000000")
        schedule = generate_amortization(principal, Decimal("8.5"), 240)

        total_principal = sum(entry.principal + entry.prepayment for entry in schedule)
        assert abs(total_principal - principal) <= Decimal("2"), (
            f"Principal sum {total_principal} differs from original {principal} "
            f"by more than 2 rupees (rounding accumulation over {len(schedule)} months)"
        )

    def test_last_entry_balance_is_zero(self):
        """The balance on the last amortization entry must be 0."""
        schedule = generate_amortization(Decimal("1000000"), Decimal("12"), 60)
        assert schedule[-1].balance == Decimal("0"), (
            f"Last balance should be 0 but got {schedule[-1].balance}"
        )

    def test_schedule_length_equals_tenure_without_prepayment(self):
        """Without prepayments, schedule should have exactly tenure_months entries."""
        tenure = 60
        schedule = generate_amortization(Decimal("1000000"), Decimal("12"), tenure)
        assert len(schedule) == tenure

    def test_prepayment_reduces_schedule_length(self):
        """Monthly prepayment should close the loan faster (fewer entries)."""
        tenure = 240
        principal = Decimal("5000000")
        rate = Decimal("8.5")

        schedule_no_prepay = generate_amortization(principal, rate, tenure)
        schedule_with_prepay = generate_amortization(
            principal, rate, tenure, monthly_prepayment=Decimal("10000")
        )

        assert len(schedule_with_prepay) < len(schedule_no_prepay), (
            f"Prepayment schedule ({len(schedule_with_prepay)} months) should be "
            f"shorter than baseline ({len(schedule_no_prepay)} months)"
        )

    def test_lump_sum_prepayment_reduces_tenure(self):
        """A single lump-sum at month 12 should reduce total months."""
        tenure = 120
        principal = Decimal("1000000")
        rate = Decimal("10")

        schedule_baseline = generate_amortization(principal, rate, tenure)
        schedule_lump = generate_amortization(
            principal, rate, tenure,
            lump_sums={12: Decimal("200000")},
        )

        assert len(schedule_lump) < len(schedule_baseline)

    def test_cumulative_interest_increases_monotonically(self):
        """Cumulative interest must never decrease."""
        schedule = generate_amortization(Decimal("500000"), Decimal("10"), 60)

        for i in range(1, len(schedule)):
            assert schedule[i].cumulative_interest >= schedule[i - 1].cumulative_interest

    def test_interest_decreases_over_time(self):
        """In reducing balance, the interest component should generally decrease."""
        schedule = generate_amortization(Decimal("1000000"), Decimal("12"), 60)

        # First month interest should be more than last month interest
        assert schedule[0].interest > schedule[-1].interest

    def test_principal_portion_increases_over_time(self):
        """In reducing balance, the principal component should generally increase."""
        schedule = generate_amortization(Decimal("1000000"), Decimal("12"), 60)

        # First month principal should be less than a mid-schedule principal
        assert schedule[0].principal < schedule[len(schedule) // 2].principal

    def test_zero_principal_returns_empty(self):
        """Zero principal should return empty schedule."""
        schedule = generate_amortization(Decimal("0"), Decimal("8.5"), 240)
        assert schedule == []

    def test_negative_principal_returns_empty(self):
        """Negative principal should return empty schedule."""
        schedule = generate_amortization(Decimal("-100000"), Decimal("8.5"), 120)
        assert schedule == []

    def test_zero_tenure_returns_empty(self):
        """Zero tenure should return empty schedule."""
        schedule = generate_amortization(Decimal("100000"), Decimal("8.5"), 0)
        assert schedule == []

    def test_zero_rate_amortization(self):
        """0% rate: all interest entries should be 0, all principal = EMI."""
        schedule = generate_amortization(Decimal("120000"), Decimal("0"), 12)

        for entry in schedule:
            assert entry.interest == Decimal("0")
        assert schedule[-1].balance == Decimal("0")

    def test_month_numbering_starts_at_one(self):
        """First entry should be month 1."""
        schedule = generate_amortization(Decimal("100000"), Decimal("10"), 12)
        assert schedule[0].month == 1

    def test_month_numbering_is_sequential(self):
        """Month numbers should be contiguous integers."""
        schedule = generate_amortization(Decimal("100000"), Decimal("10"), 12)
        months = [entry.month for entry in schedule]
        assert months == list(range(1, len(schedule) + 1))

    def test_prepayment_recorded_in_entries(self):
        """Monthly prepayment amounts must appear in AmortizationEntry.prepayment."""
        prepay = Decimal("5000")
        schedule = generate_amortization(
            Decimal("500000"), Decimal("10"), 60,
            monthly_prepayment=prepay,
        )
        # At least early entries should show the full prepayment
        assert schedule[0].prepayment == prepay

    def test_large_prepayment_caps_at_balance(self):
        """Prepayment should not push balance below zero."""
        schedule = generate_amortization(
            Decimal("50000"), Decimal("10"), 60,
            monthly_prepayment=Decimal("50000"),
        )
        for entry in schedule:
            assert entry.balance >= Decimal("0")


# =====================================================================
# TOTAL INTEREST TESTS
# =====================================================================

class TestCalculateTotalInterest:
    """Tests for calculating total interest over loan lifetime."""

    def test_total_interest_is_positive(self):
        """Any loan with rate > 0 should have positive total interest."""
        interest = calculate_total_interest(Decimal("1000000"), Decimal("12"), 60)
        assert interest > Decimal("0")

    def test_total_interest_zero_rate(self):
        """0% rate should have zero (or negligible rounding residual) total interest."""
        interest = calculate_total_interest(Decimal("1000000"), Decimal("0"), 60)
        assert interest <= Decimal("1"), (
            f"0% rate interest should be ~0 but got {interest}"
        )

    def test_longer_tenure_more_interest(self):
        """Longer tenure means more total interest paid (same P, r)."""
        interest_short = calculate_total_interest(Decimal("1000000"), Decimal("10"), 60)
        interest_long = calculate_total_interest(Decimal("1000000"), Decimal("10"), 240)
        assert interest_long > interest_short

    def test_higher_rate_more_interest(self):
        """Higher rate means more total interest (same P, n)."""
        interest_low = calculate_total_interest(Decimal("1000000"), Decimal("8"), 120)
        interest_high = calculate_total_interest(Decimal("1000000"), Decimal("14"), 120)
        assert interest_high > interest_low


# =====================================================================
# INTEREST SAVED TESTS
# =====================================================================

class TestCalculateInterestSaved:
    """Tests for interest and tenure savings with prepayments."""

    def test_interest_saved_is_positive_with_prepayment(self):
        """Any prepayment should save some interest."""
        saved, months = calculate_interest_saved(
            Decimal("1000000"), Decimal("12"), 60,
            monthly_prepayment=Decimal("5000"),
        )
        assert saved > Decimal("0"), f"Interest saved should be > 0, got {saved}"
        assert months > 0, f"Months saved should be > 0, got {months}"

    def test_no_prepayment_no_savings(self):
        """Zero prepayment should yield zero (or negligible rounding residual) savings."""
        saved, months = calculate_interest_saved(
            Decimal("1000000"), Decimal("12"), 60,
        )
        assert saved <= Decimal("1"), (
            f"No-prepayment interest saved should be ~0 but got {saved}"
        )
        assert months == 0

    def test_larger_prepayment_saves_more(self):
        """Larger monthly prepayment should save more interest."""
        saved_small, _ = calculate_interest_saved(
            Decimal("1000000"), Decimal("12"), 60,
            monthly_prepayment=Decimal("2000"),
        )
        saved_large, _ = calculate_interest_saved(
            Decimal("1000000"), Decimal("12"), 60,
            monthly_prepayment=Decimal("10000"),
        )
        assert saved_large > saved_small

    def test_lump_sum_saves_interest(self):
        """A lump sum payment should save interest."""
        saved, months = calculate_interest_saved(
            Decimal("1000000"), Decimal("12"), 60,
            lump_sums={6: Decimal("100000")},
        )
        assert saved > Decimal("0")
        assert months > 0

    def test_interest_saved_does_not_exceed_total_interest(self):
        """Interest saved should never exceed total baseline interest."""
        principal = Decimal("500000")
        rate = Decimal("10")
        tenure = 60
        total = calculate_total_interest(principal, rate, tenure)
        saved, _ = calculate_interest_saved(
            principal, rate, tenure,
            monthly_prepayment=Decimal("50000"),
        )
        assert saved <= total


# =====================================================================
# REVERSE EMI RATE SOLVER TESTS
# =====================================================================

class TestReverseEMIRate:
    """Tests for binary-search rate solver."""

    def test_known_emi_returns_known_rate(self):
        """Given known EMI/principal/tenure, solver should return the correct rate.

        HDFC benchmark: 10,00,000 at 12% for 60 months = 22,244.
        """
        rate = reverse_emi_rate(
            principal=Decimal("1000000"),
            emi=Decimal("22244"),
            tenure_months=60,
        )
        # Should be close to 12%
        assert abs(rate - Decimal("12")) <= Decimal("0.10"), (
            f"Expected rate ~12.00% but got {rate}%"
        )

    def test_sbi_home_rate_recovery(self):
        """SBI benchmark: 50,00,000 at 8.5% for 240 months = 43,391."""
        rate = reverse_emi_rate(
            principal=Decimal("5000000"),
            emi=Decimal("43391"),
            tenure_months=240,
        )
        assert abs(rate - Decimal("8.5")) <= Decimal("0.10"), (
            f"Expected rate ~8.50% but got {rate}%"
        )

    def test_higher_emi_implies_higher_rate(self):
        """If EMI is higher (same P, n), the derived rate should be higher."""
        rate_low = reverse_emi_rate(Decimal("1000000"), Decimal("15000"), 120)
        rate_high = reverse_emi_rate(Decimal("1000000"), Decimal("20000"), 120)
        assert rate_high > rate_low

    def test_returns_decimal(self):
        """Result should be a Decimal quantized to 0.01."""
        rate = reverse_emi_rate(Decimal("500000"), Decimal("11000"), 60)
        assert isinstance(rate, Decimal)
        assert rate == rate.quantize(Decimal("0.01"))


# =====================================================================
# REVERSE EMI TENURE SOLVER TESTS
# =====================================================================

class TestReverseEMITenure:
    """Tests for tenure solver given EMI and rate."""

    def test_known_case(self):
        """HDFC: 10,00,000 at 12% with EMI 22,244 should give ~60 months."""
        tenure = reverse_emi_tenure(
            principal=Decimal("1000000"),
            emi=Decimal("22244"),
            annual_rate=Decimal("12"),
        )
        assert abs(tenure - 60) <= 1, f"Expected ~60 months, got {tenure}"

    def test_zero_rate(self):
        """0% rate: tenure = principal / EMI."""
        tenure = reverse_emi_tenure(
            principal=Decimal("120000"),
            emi=Decimal("10000"),
            annual_rate=Decimal("0"),
        )
        assert tenure == 12

    def test_emi_too_small_returns_zero(self):
        """If EMI cannot even cover monthly interest, return 0 (impossible)."""
        tenure = reverse_emi_tenure(
            principal=Decimal("10000000"),
            emi=Decimal("1000"),  # Way too small for 10% on 1 crore
            annual_rate=Decimal("10"),
        )
        assert tenure == 0

    def test_higher_emi_means_shorter_tenure(self):
        """Doubling the EMI should roughly halve the tenure (or less)."""
        tenure_low = reverse_emi_tenure(Decimal("1000000"), Decimal("15000"), Decimal("10"))
        tenure_high = reverse_emi_tenure(Decimal("1000000"), Decimal("30000"), Decimal("10"))
        assert tenure_high < tenure_low


# =====================================================================
# AFFORDABILITY TESTS
# =====================================================================

class TestCalculateAffordability:
    """Tests for max-principal-from-EMI calculator."""

    def test_known_affordability(self):
        """If EMI = 43,391 at 8.5% for 240 months, max principal should be ~50,00,000."""
        max_principal = calculate_affordability(
            emi=Decimal("43391"),
            annual_rate=Decimal("8.5"),
            tenure_months=240,
        )
        # Should be close to 50 lakh
        assert abs(max_principal - Decimal("5000000")) <= Decimal("5000"), (
            f"Expected ~50,00,000 but got {max_principal}"
        )

    def test_zero_emi_returns_zero(self):
        """Zero EMI budget should give zero borrowable amount."""
        result = calculate_affordability(Decimal("0"), Decimal("9"), 120)
        assert result == Decimal("0")

    def test_negative_emi_returns_zero(self):
        """Negative EMI budget should give zero borrowable amount."""
        result = calculate_affordability(Decimal("-5000"), Decimal("9"), 120)
        assert result == Decimal("0")

    def test_zero_tenure_returns_zero(self):
        """Zero tenure should give zero borrowable amount."""
        result = calculate_affordability(Decimal("20000"), Decimal("9"), 0)
        assert result == Decimal("0")

    def test_zero_rate_affordability(self):
        """At 0% rate, affordability = EMI * tenure."""
        max_principal = calculate_affordability(
            emi=Decimal("10000"),
            annual_rate=Decimal("0"),
            tenure_months=120,
        )
        expected = Decimal("1200000")  # 10,000 * 120
        assert max_principal == expected.quantize(PAISA)

    def test_higher_rate_means_lower_affordability(self):
        """Higher rate should reduce borrowable principal for the same EMI."""
        p_low = calculate_affordability(Decimal("30000"), Decimal("8"), 240)
        p_high = calculate_affordability(Decimal("30000"), Decimal("12"), 240)
        assert p_low > p_high

    def test_longer_tenure_means_higher_affordability(self):
        """Longer tenure should increase borrowable principal for the same EMI."""
        p_short = calculate_affordability(Decimal("30000"), Decimal("9"), 60)
        p_long = calculate_affordability(Decimal("30000"), Decimal("9"), 240)
        assert p_long > p_short

    def test_emi_affordability_roundtrip(self):
        """calculate_emi(affordability(emi, r, n), r, n) should return ~ emi."""
        emi_budget = Decimal("25000")
        rate = Decimal("10")
        tenure = 120

        max_p = calculate_affordability(emi_budget, rate, tenure)
        roundtrip_emi = calculate_emi(max_p, rate, tenure)

        assert abs(roundtrip_emi - emi_budget) <= Decimal("1"), (
            f"Roundtrip EMI {roundtrip_emi} differs from budget {emi_budget}"
        )
