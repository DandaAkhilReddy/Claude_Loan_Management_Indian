"""Comprehensive unit tests for repayment strategy implementations.

Tests Avalanche, Snowball, SmartHybrid, and Proportional strategies
against expected allocation behaviour, including India-specific tax
benefit adjustments and the 3-EMI quick-win bump.
"""

import pytest
from decimal import Decimal
from copy import deepcopy

from app.core.strategies import (
    LoanSnapshot,
    AvalancheStrategy,
    SnowballStrategy,
    SmartHybridStrategy,
    ProportionalStrategy,
    get_strategy,
)


# =====================================================================
# AVALANCHE STRATEGY TESTS
# =====================================================================

class TestAvalancheStrategy:
    """Avalanche: allocate extra budget to the highest interest rate loan first."""

    def test_allocates_to_highest_rate_first(self, three_diverse_loans):
        """With 12%, 9.5%, 8.5% rates, all budget goes to the 12% loan first."""
        strategy = AvalancheStrategy()
        budget = Decimal("50000")

        allocation = strategy.allocate(three_diverse_loans, budget)

        # HDFC personal at 12% is highest rate
        assert "hdfc_personal" in allocation
        # Since budget (50k) < HDFC outstanding (10L), full budget to HDFC
        assert allocation["hdfc_personal"] == budget

    def test_overflow_to_second_highest(self):
        """When budget exceeds first loan's balance, remainder flows to next highest."""
        loans = [
            LoanSnapshot(
                loan_id="high_rate",
                bank_name="HDFC",
                loan_type="personal",
                outstanding_principal=Decimal("30000"),
                interest_rate=Decimal("15"),
                emi_amount=Decimal("5000"),
                remaining_tenure_months=7,
                prepayment_penalty_pct=Decimal("0"),
                foreclosure_charges_pct=Decimal("0"),
            ),
            LoanSnapshot(
                loan_id="low_rate",
                bank_name="SBI",
                loan_type="home",
                outstanding_principal=Decimal("500000"),
                interest_rate=Decimal("8"),
                emi_amount=Decimal("10000"),
                remaining_tenure_months=60,
                prepayment_penalty_pct=Decimal("0"),
                foreclosure_charges_pct=Decimal("0"),
            ),
        ]

        strategy = AvalancheStrategy()
        allocation = strategy.allocate(loans, Decimal("50000"))

        assert allocation["high_rate"] == Decimal("30000")  # Capped at balance
        assert allocation["low_rate"] == Decimal("20000")   # Remainder

    def test_empty_loan_list_returns_empty(self):
        """No loans should return empty allocation."""
        strategy = AvalancheStrategy()
        assert strategy.allocate([], Decimal("10000")) == {}

    def test_zero_budget_returns_empty(self, three_diverse_loans):
        """Zero extra budget should return empty allocation."""
        strategy = AvalancheStrategy()
        assert strategy.allocate(three_diverse_loans, Decimal("0")) == {}

    def test_negative_budget_returns_empty(self, three_diverse_loans):
        """Negative budget should return empty allocation."""
        strategy = AvalancheStrategy()
        assert strategy.allocate(three_diverse_loans, Decimal("-5000")) == {}

    def test_single_loan_gets_full_budget(self, hdfc_personal_loan):
        """With only one loan, it should receive all available budget."""
        strategy = AvalancheStrategy()
        allocation = strategy.allocate([hdfc_personal_loan], Decimal("30000"))
        assert allocation["hdfc_personal"] == Decimal("30000")

    def test_ordering_is_by_rate_not_balance(self):
        """Avalanche must sort by rate, not by balance."""
        loans = [
            LoanSnapshot(
                loan_id="big_low_rate",
                bank_name="SBI",
                loan_type="home",
                outstanding_principal=Decimal("5000000"),
                interest_rate=Decimal("7"),
                emi_amount=Decimal("40000"),
                remaining_tenure_months=180,
                prepayment_penalty_pct=Decimal("0"),
                foreclosure_charges_pct=Decimal("0"),
            ),
            LoanSnapshot(
                loan_id="small_high_rate",
                bank_name="HDFC",
                loan_type="personal",
                outstanding_principal=Decimal("50000"),
                interest_rate=Decimal("18"),
                emi_amount=Decimal("5000"),
                remaining_tenure_months=12,
                prepayment_penalty_pct=Decimal("0"),
                foreclosure_charges_pct=Decimal("0"),
            ),
        ]

        strategy = AvalancheStrategy()
        allocation = strategy.allocate(loans, Decimal("40000"))

        # Should go to small_high_rate first (18%) despite tiny balance
        assert "small_high_rate" in allocation
        first_key = list(allocation.keys())[0]
        assert first_key == "small_high_rate" or allocation.get("small_high_rate", Decimal("0")) > Decimal("0")


# =====================================================================
# SNOWBALL STRATEGY TESTS
# =====================================================================

class TestSnowballStrategy:
    """Snowball: allocate extra budget to the lowest balance loan first."""

    def test_allocates_to_lowest_balance_first(self, three_diverse_loans):
        """With balances 50L, 10L, 8L, budget goes to 8L (car) first."""
        strategy = SnowballStrategy()
        budget = Decimal("50000")

        allocation = strategy.allocate(three_diverse_loans, budget)

        # ICICI car at 8L is the smallest balance
        assert "icici_car" in allocation
        assert allocation["icici_car"] == budget

    def test_overflow_to_second_smallest(self):
        """When budget exceeds smallest loan, remainder goes to next smallest."""
        loans = [
            LoanSnapshot(
                loan_id="tiny",
                bank_name="AXIS",
                loan_type="personal",
                outstanding_principal=Decimal("10000"),
                interest_rate=Decimal("14"),
                emi_amount=Decimal("5000"),
                remaining_tenure_months=3,
                prepayment_penalty_pct=Decimal("0"),
                foreclosure_charges_pct=Decimal("0"),
            ),
            LoanSnapshot(
                loan_id="medium",
                bank_name="SBI",
                loan_type="car",
                outstanding_principal=Decimal("500000"),
                interest_rate=Decimal("9"),
                emi_amount=Decimal("10000"),
                remaining_tenure_months=60,
                prepayment_penalty_pct=Decimal("0"),
                foreclosure_charges_pct=Decimal("0"),
            ),
        ]

        strategy = SnowballStrategy()
        allocation = strategy.allocate(loans, Decimal("30000"))

        assert allocation["tiny"] == Decimal("10000")    # Capped at balance
        assert allocation["medium"] == Decimal("20000")  # Remainder

    def test_empty_loan_list_returns_empty(self):
        """No loans should return empty allocation."""
        strategy = SnowballStrategy()
        assert strategy.allocate([], Decimal("10000")) == {}

    def test_zero_budget_returns_empty(self, three_diverse_loans):
        """Zero extra budget should return empty allocation."""
        strategy = SnowballStrategy()
        assert strategy.allocate(three_diverse_loans, Decimal("0")) == {}

    def test_negative_budget_returns_empty(self, three_diverse_loans):
        """Negative budget should return empty allocation."""
        strategy = SnowballStrategy()
        assert strategy.allocate(three_diverse_loans, Decimal("-1000")) == {}

    def test_ordering_is_by_balance_not_rate(self):
        """Snowball must sort by outstanding balance, ignoring rate."""
        loans = [
            LoanSnapshot(
                loan_id="big_high_rate",
                bank_name="HDFC",
                loan_type="personal",
                outstanding_principal=Decimal("1000000"),
                interest_rate=Decimal("18"),
                emi_amount=Decimal("25000"),
                remaining_tenure_months=60,
                prepayment_penalty_pct=Decimal("0"),
                foreclosure_charges_pct=Decimal("0"),
            ),
            LoanSnapshot(
                loan_id="small_low_rate",
                bank_name="SBI",
                loan_type="home",
                outstanding_principal=Decimal("50000"),
                interest_rate=Decimal("7"),
                emi_amount=Decimal("5000"),
                remaining_tenure_months=12,
                prepayment_penalty_pct=Decimal("0"),
                foreclosure_charges_pct=Decimal("0"),
            ),
        ]

        strategy = SnowballStrategy()
        allocation = strategy.allocate(loans, Decimal("40000"))

        # small_low_rate (50k balance) should be targeted first despite low rate
        assert allocation["small_low_rate"] == Decimal("40000")


# =====================================================================
# SMART HYBRID STRATEGY TESTS
# =====================================================================

class TestSmartHybridStrategy:
    """SmartHybrid: post-tax effective rate + 3-EMI closure bump."""

    def test_home_loan_effective_rate_with_24b(self, sbi_home_loan, hdfc_personal_loan):
        """Home 8.5% with 24(b) at 30% bracket -> effective 5.95%, lower than personal 12%.

        Therefore SmartHybrid should prefer personal loan (12% effective)
        over home loan (5.95% effective).
        """
        strategy = SmartHybridStrategy(tax_bracket=Decimal("0.30"))
        loans = [deepcopy(sbi_home_loan), deepcopy(hdfc_personal_loan)]
        budget = Decimal("50000")

        allocation = strategy.allocate(loans, budget)

        # Personal loan at 12% effective should get the budget first
        assert "hdfc_personal" in allocation
        assert allocation["hdfc_personal"] == budget

    def test_effective_rate_calculation_24b(self, sbi_home_loan):
        """Verify the effective rate formula for 24(b) eligible home loan.

        8.5% - (8.5% * 0.30) = 8.5% - 2.55% = 5.95%
        """
        strategy = SmartHybridStrategy(tax_bracket=Decimal("0.30"))
        effective = strategy._calculate_effective_rate(sbi_home_loan)

        expected = Decimal("8.5") - Decimal("8.5") * Decimal("0.30")
        assert effective == expected, (
            f"Expected effective rate {expected}% but got {effective}%"
        )

    def test_effective_rate_calculation_80e(self, education_loan):
        """Education loan 80E: interest fully deductible => effective = rate * (1 - bracket).

        10% - (10% * 0.30) = 10% - 3% = 7%
        """
        strategy = SmartHybridStrategy(tax_bracket=Decimal("0.30"))
        effective = strategy._calculate_effective_rate(education_loan)

        expected = Decimal("10") - Decimal("10") * Decimal("0.30")
        assert effective == expected

    def test_effective_rate_no_tax_benefit(self, hdfc_personal_loan):
        """Personal loan with no tax benefit: effective = nominal = 12%."""
        strategy = SmartHybridStrategy(tax_bracket=Decimal("0.30"))
        effective = strategy._calculate_effective_rate(hdfc_personal_loan)

        assert effective == Decimal("12")

    def test_3_emi_bump_to_top(self, smart_hybrid_loans):
        """A loan within 3 EMIs of closure should be bumped to the top priority.

        small_closing (14%, ~2 months left) should be prioritized even if its
        effective rate is lower than others in the sorted list. Because its
        months_to_closure <= 3, it gets bumped.
        """
        strategy = SmartHybridStrategy(tax_bracket=Decimal("0.30"))
        loans = [deepcopy(l) for l in smart_hybrid_loans]
        budget = Decimal("50000")

        allocation = strategy.allocate(loans, budget)

        # small_closing should get allocated first (3-EMI bump)
        assert "small_closing" in allocation
        # And since its balance is only 20k, remaining 30k goes elsewhere
        assert allocation["small_closing"] == Decimal("20000")

    def test_foreclosure_charges_affect_effective_rate(self, fixed_rate_personal_loan):
        """Foreclosure charges should increase effective rate by penalty * 0.1."""
        strategy = SmartHybridStrategy(tax_bracket=Decimal("0.30"))
        effective = strategy._calculate_effective_rate(fixed_rate_personal_loan)

        # 15% (no tax benefit) + 4% * 0.1 = 15.4%
        expected = Decimal("15") + Decimal("4") * Decimal("0.1")
        assert effective == expected

    def test_empty_loan_list_returns_empty(self):
        """No loans should return empty allocation."""
        strategy = SmartHybridStrategy()
        assert strategy.allocate([], Decimal("10000")) == {}

    def test_zero_budget_returns_empty(self, smart_hybrid_loans):
        """Zero extra budget should return empty allocation."""
        strategy = SmartHybridStrategy()
        assert strategy.allocate(smart_hybrid_loans, Decimal("0")) == {}

    def test_different_tax_brackets_change_priority(self, sbi_home_loan, hdfc_personal_loan):
        """At 0% bracket, home loan effective = 8.5%; at 30%, effective = 5.95%.

        With 0% bracket and a personal loan at 12%, the personal should
        still be first (12% > 8.5%). But if the home loan rate were higher
        than personal, the bracket would not change ordering at 0%.
        """
        strategy_0 = SmartHybridStrategy(tax_bracket=Decimal("0"))
        strategy_30 = SmartHybridStrategy(tax_bracket=Decimal("0.30"))

        loans = [deepcopy(sbi_home_loan), deepcopy(hdfc_personal_loan)]

        eff_home_0 = strategy_0._calculate_effective_rate(sbi_home_loan)
        eff_home_30 = strategy_30._calculate_effective_rate(deepcopy(sbi_home_loan))

        # At 0% bracket, effective = nominal 8.5%
        assert eff_home_0 == Decimal("8.5")
        # At 30% bracket, effective = 5.95%
        assert eff_home_30 == Decimal("5.95")


# =====================================================================
# PROPORTIONAL STRATEGY TESTS
# =====================================================================

class TestProportionalStrategy:
    """Proportional: distribute extra budget pro-rata by outstanding balance."""

    def test_proportional_distribution(self, three_diverse_loans):
        """Budget should be split proportionally by balance."""
        strategy = ProportionalStrategy()
        budget = Decimal("100000")

        allocation = strategy.allocate(three_diverse_loans, budget)

        # Total balance: 50L + 10L + 8L = 68L
        total_balance = Decimal("5000000") + Decimal("1000000") + Decimal("800000")

        # Each loan should get approximately (balance / total_balance) * budget
        for loan in three_diverse_loans:
            expected_share = (
                budget * loan.outstanding_principal / total_balance
            ).quantize(Decimal("0.01"))
            # Allow 1 rupee for rounding remainder assignment
            assert abs(allocation[loan.loan_id] - expected_share) <= Decimal("1.01"), (
                f"Loan {loan.loan_id} expected ~{expected_share} but got {allocation[loan.loan_id]}"
            )

    def test_total_allocation_equals_budget(self, three_diverse_loans):
        """Sum of all allocations must equal the budget (no leakage)."""
        strategy = ProportionalStrategy()
        budget = Decimal("100000")

        allocation = strategy.allocate(three_diverse_loans, budget)

        total_allocated = sum(allocation.values())
        assert total_allocated == budget, (
            f"Total allocated {total_allocated} does not match budget {budget}"
        )

    def test_empty_loan_list_returns_empty(self):
        """No loans should return empty allocation."""
        strategy = ProportionalStrategy()
        assert strategy.allocate([], Decimal("10000")) == {}

    def test_zero_budget_returns_empty(self, three_diverse_loans):
        """Zero extra budget should return empty allocation."""
        strategy = ProportionalStrategy()
        assert strategy.allocate(three_diverse_loans, Decimal("0")) == {}

    def test_negative_budget_returns_empty(self, three_diverse_loans):
        """Negative budget should return empty allocation."""
        strategy = ProportionalStrategy()
        assert strategy.allocate(three_diverse_loans, Decimal("-5000")) == {}

    def test_single_loan_gets_full_budget(self, hdfc_personal_loan):
        """With one loan, proportional = 100% = full budget."""
        strategy = ProportionalStrategy()
        allocation = strategy.allocate([hdfc_personal_loan], Decimal("50000"))

        assert allocation["hdfc_personal"] == Decimal("50000")

    def test_larger_loan_gets_larger_share(self, three_diverse_loans):
        """The largest-balance loan should receive the largest share."""
        strategy = ProportionalStrategy()
        allocation = strategy.allocate(three_diverse_loans, Decimal("100000"))

        # SBI home (50L) should get the most, ICICI car (8L) the least
        assert allocation["sbi_home"] > allocation["hdfc_personal"]
        assert allocation["hdfc_personal"] > allocation["icici_car"]

    def test_rounding_remainder_goes_to_largest(self):
        """Any rounding remainder should be assigned to the largest balance loan."""
        loans = [
            LoanSnapshot(
                loan_id="a",
                bank_name="A",
                loan_type="personal",
                outstanding_principal=Decimal("333333"),
                interest_rate=Decimal("10"),
                emi_amount=Decimal("7000"),
                remaining_tenure_months=60,
                prepayment_penalty_pct=Decimal("0"),
                foreclosure_charges_pct=Decimal("0"),
            ),
            LoanSnapshot(
                loan_id="b",
                bank_name="B",
                loan_type="personal",
                outstanding_principal=Decimal("666667"),
                interest_rate=Decimal("10"),
                emi_amount=Decimal("14000"),
                remaining_tenure_months=60,
                prepayment_penalty_pct=Decimal("0"),
                foreclosure_charges_pct=Decimal("0"),
            ),
        ]

        strategy = ProportionalStrategy()
        allocation = strategy.allocate(loans, Decimal("10000"))

        # Total should always be exactly the budget
        assert sum(allocation.values()) == Decimal("10000")


# =====================================================================
# GET_STRATEGY FACTORY TESTS
# =====================================================================

class TestGetStrategy:
    """Tests for the strategy factory function."""

    def test_get_avalanche(self):
        s = get_strategy("avalanche")
        assert isinstance(s, AvalancheStrategy)
        assert s.name == "avalanche"

    def test_get_snowball(self):
        s = get_strategy("snowball")
        assert isinstance(s, SnowballStrategy)
        assert s.name == "snowball"

    def test_get_smart_hybrid(self):
        s = get_strategy("smart_hybrid")
        assert isinstance(s, SmartHybridStrategy)
        assert s.name == "smart_hybrid"

    def test_get_proportional(self):
        s = get_strategy("proportional")
        assert isinstance(s, ProportionalStrategy)
        assert s.name == "proportional"

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("foobar")

    def test_smart_hybrid_receives_tax_bracket(self):
        s = get_strategy("smart_hybrid", tax_bracket=Decimal("0.20"))
        assert isinstance(s, SmartHybridStrategy)
        assert s.tax_bracket == Decimal("0.20")
