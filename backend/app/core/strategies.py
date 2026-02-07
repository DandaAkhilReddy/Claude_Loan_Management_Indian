"""Repayment strategy implementations for multi-loan optimization.

4 strategies:
- Avalanche: Highest interest rate first (mathematically optimal)
- Snowball: Lowest balance first (psychological wins)
- Smart Hybrid: Post-tax effective rate + 3-EMI bump + foreclosure awareness
- Proportional: Pro-rata by outstanding balance
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class LoanSnapshot:
    """Snapshot of a loan at a point in time during optimization."""
    loan_id: str
    bank_name: str
    loan_type: str  # home/personal/car/education/gold/credit_card
    outstanding_principal: Decimal
    interest_rate: Decimal  # Annual %
    emi_amount: Decimal
    remaining_tenure_months: int
    prepayment_penalty_pct: Decimal  # 0 for floating rate (RBI 2014)
    foreclosure_charges_pct: Decimal
    # Tax benefit fields
    eligible_80c: bool = False
    eligible_24b: bool = False
    eligible_80e: bool = False
    eligible_80eea: bool = False
    # Derived
    effective_rate: Decimal = Decimal("0")  # Post-tax rate
    months_to_closure: int = 0  # Estimated months left


class RepaymentStrategy(ABC):
    """Base class for all repayment strategies."""

    name: str
    description: str

    @abstractmethod
    def allocate(
        self,
        active_loans: list[LoanSnapshot],
        extra_budget: Decimal,
    ) -> dict[str, Decimal]:
        """Allocate extra payment budget across active loans.

        Args:
            active_loans: Currently active (unpaid) loans
            extra_budget: Total extra money available this month

        Returns:
            Dict of {loan_id: extra_amount_to_pay}
        """
        ...


class AvalancheStrategy(RepaymentStrategy):
    """Pay highest interest rate loan first. Saves the most interest."""

    name = "avalanche"
    description = "Pay Least Interest — targets highest rate loan first"

    def allocate(self, active_loans: list[LoanSnapshot], extra_budget: Decimal) -> dict[str, Decimal]:
        if not active_loans or extra_budget <= 0:
            return {}

        # Sort by interest rate descending
        sorted_loans = sorted(active_loans, key=lambda l: l.interest_rate, reverse=True)
        allocation: dict[str, Decimal] = {}
        remaining = extra_budget

        for loan in sorted_loans:
            if remaining <= 0:
                break
            # Allocate up to outstanding principal (minus this month's EMI principal portion)
            max_prepayment = loan.outstanding_principal
            payment = min(remaining, max_prepayment)
            if payment > 0:
                allocation[loan.loan_id] = payment
                remaining -= payment

        return allocation


class SnowballStrategy(RepaymentStrategy):
    """Pay smallest balance loan first. Fastest psychological wins."""

    name = "snowball"
    description = "Fastest Quick Wins — eliminates smallest loan first"

    def allocate(self, active_loans: list[LoanSnapshot], extra_budget: Decimal) -> dict[str, Decimal]:
        if not active_loans or extra_budget <= 0:
            return {}

        # Sort by outstanding balance ascending
        sorted_loans = sorted(active_loans, key=lambda l: l.outstanding_principal)
        allocation: dict[str, Decimal] = {}
        remaining = extra_budget

        for loan in sorted_loans:
            if remaining <= 0:
                break
            max_prepayment = loan.outstanding_principal
            payment = min(remaining, max_prepayment)
            if payment > 0:
                allocation[loan.loan_id] = payment
                remaining -= payment

        return allocation


class SmartHybridStrategy(RepaymentStrategy):
    """India-specific smart strategy: post-tax effective rates + psychological bumps.

    Algorithm:
    1. Calculate effective_rate = nominal_rate - tax_benefit_rate
       Example: Home loan 8.5% with 24(b) at 30% bracket → effective = 5.95%
    2. Sort by effective_rate DESC (avalanche base layer)
    3. Bump any loan within 3 EMIs of closure to TOP (quick win)
    4. Factor in foreclosure_charges (penalizes fixed-rate early payoff)
    """

    name = "smart_hybrid"
    description = "Smart Hybrid (Recommended) — post-tax optimized with quick wins"

    def __init__(self, tax_bracket: Decimal = Decimal("0.30")):
        self.tax_bracket = tax_bracket

    def _calculate_effective_rate(self, loan: LoanSnapshot) -> Decimal:
        """Calculate post-tax effective interest rate."""
        tax_benefit_rate = Decimal("0")

        if loan.eligible_24b:
            # Section 24(b): Home loan interest deduction
            tax_benefit_rate = loan.interest_rate * self.tax_bracket
        elif loan.eligible_80e:
            # Section 80E: Education loan interest (full deduction)
            tax_benefit_rate = loan.interest_rate * self.tax_bracket
        elif loan.eligible_80c:
            # Section 80C: Principal deduction (partial benefit)
            tax_benefit_rate = loan.interest_rate * self.tax_bracket * Decimal("0.5")

        effective = loan.interest_rate - tax_benefit_rate

        # Factor in foreclosure charges (increases effective cost of early payoff)
        if loan.foreclosure_charges_pct > 0:
            effective += loan.foreclosure_charges_pct * Decimal("0.1")

        return effective

    def _estimate_months_to_closure(self, loan: LoanSnapshot, extra_per_month: Decimal) -> int:
        """Estimate how many months until this loan is paid off with extra payments."""
        if loan.emi_amount + extra_per_month <= 0:
            return 999

        r = loan.interest_rate / Decimal("1200")
        balance = loan.outstanding_principal
        months = 0
        total_monthly = loan.emi_amount + extra_per_month

        while balance > 0 and months < 600:
            interest = balance * r
            principal_paid = total_monthly - interest
            if principal_paid <= 0:
                return 999
            balance -= principal_paid
            months += 1

        return months

    def allocate(self, active_loans: list[LoanSnapshot], extra_budget: Decimal) -> dict[str, Decimal]:
        if not active_loans or extra_budget <= 0:
            return {}

        # Calculate effective rates
        for loan in active_loans:
            loan.effective_rate = self._calculate_effective_rate(loan)
            loan.months_to_closure = self._estimate_months_to_closure(loan, Decimal("0"))

        # Sort by effective rate descending (avalanche base)
        sorted_loans = sorted(active_loans, key=lambda l: l.effective_rate, reverse=True)

        # Bump loans within 3 EMIs of closure to the top (quick win)
        quick_wins = [l for l in sorted_loans if l.months_to_closure <= 3]
        others = [l for l in sorted_loans if l.months_to_closure > 3]
        sorted_loans = quick_wins + others

        allocation: dict[str, Decimal] = {}
        remaining = extra_budget

        for loan in sorted_loans:
            if remaining <= 0:
                break
            # Skip loans with high foreclosure charges if penalty exceeds benefit
            max_prepayment = loan.outstanding_principal
            payment = min(remaining, max_prepayment)
            if payment > 0:
                allocation[loan.loan_id] = payment
                remaining -= payment

        return allocation


class ProportionalStrategy(RepaymentStrategy):
    """Distribute extra payment proportionally by outstanding balance."""

    name = "proportional"
    description = "Balanced — distributes extra payment across all loans"

    def allocate(self, active_loans: list[LoanSnapshot], extra_budget: Decimal) -> dict[str, Decimal]:
        if not active_loans or extra_budget <= 0:
            return {}

        total_balance = sum(l.outstanding_principal for l in active_loans)
        if total_balance <= 0:
            return {}

        allocation: dict[str, Decimal] = {}
        allocated = Decimal("0")

        for i, loan in enumerate(active_loans):
            if loan.outstanding_principal <= 0:
                continue
            share = extra_budget * loan.outstanding_principal / total_balance
            share = share.quantize(Decimal("0.01"))
            allocation[loan.loan_id] = min(share, loan.outstanding_principal)
            allocated += allocation[loan.loan_id]

        # Assign rounding remainder to largest balance
        remainder = extra_budget - allocated
        if remainder > 0 and active_loans:
            largest = max(active_loans, key=lambda l: l.outstanding_principal)
            allocation[largest.loan_id] = allocation.get(largest.loan_id, Decimal("0")) + remainder

        return allocation


def get_strategy(name: str, tax_bracket: Decimal = Decimal("0.30")) -> RepaymentStrategy:
    """Factory function to get strategy by name."""
    strategies = {
        "avalanche": AvalancheStrategy(),
        "snowball": SnowballStrategy(),
        "smart_hybrid": SmartHybridStrategy(tax_bracket),
        "proportional": ProportionalStrategy(),
    }
    if name not in strategies:
        raise ValueError(f"Unknown strategy: {name}. Choose from: {list(strategies.keys())}")
    return strategies[name]
