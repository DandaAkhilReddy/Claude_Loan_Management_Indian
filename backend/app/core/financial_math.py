"""Financial math engine — correct to the paisa.

All monetary calculations use Decimal for precision.
EMI formula: EMI = P * r * (1+r)^n / ((1+r)^n - 1) where r = annual_rate/12/100
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from dataclasses import dataclass, field

getcontext().prec = 28

PAISA = Decimal("0.01")


@dataclass
class AmortizationEntry:
    month: int
    emi: Decimal
    principal: Decimal
    interest: Decimal
    balance: Decimal
    prepayment: Decimal = Decimal("0")
    cumulative_interest: Decimal = Decimal("0")
    cumulative_principal: Decimal = Decimal("0")


def calculate_emi(
    principal: Decimal,
    annual_rate: Decimal,
    tenure_months: int,
) -> Decimal:
    """Calculate monthly EMI using reducing balance method.

    EMI = P * r * (1+r)^n / ((1+r)^n - 1)

    Verified against:
    - SBI: ₹50,00,000 at 8.5% for 240 months = ₹43,391
    - HDFC: ₹10,00,000 at 12% for 60 months = ₹22,244
    """
    if principal <= 0 or tenure_months <= 0:
        return Decimal("0")
    if annual_rate == 0:
        return (principal / tenure_months).quantize(PAISA, ROUND_HALF_UP)

    r = annual_rate / Decimal("1200")  # Monthly rate
    n = tenure_months
    factor = (1 + r) ** n
    emi = principal * r * factor / (factor - 1)
    return emi.quantize(PAISA, ROUND_HALF_UP)


def generate_amortization(
    principal: Decimal,
    annual_rate: Decimal,
    tenure_months: int,
    monthly_prepayment: Decimal = Decimal("0"),
    lump_sums: dict[int, Decimal] | None = None,
) -> list[AmortizationEntry]:
    """Generate full amortization schedule with optional prepayments.

    Args:
        principal: Original loan amount
        annual_rate: Annual interest rate (e.g., 8.5 for 8.5%)
        tenure_months: Original tenure in months
        monthly_prepayment: Extra amount paid each month beyond EMI
        lump_sums: Dict of {month_number: lump_sum_amount}

    Returns:
        List of AmortizationEntry for each month until loan is paid off.
    """
    if principal <= 0 or tenure_months <= 0:
        return []

    lump_sums = lump_sums or {}
    emi = calculate_emi(principal, annual_rate, tenure_months)
    r = annual_rate / Decimal("1200") if annual_rate > 0 else Decimal("0")

    balance = principal
    schedule: list[AmortizationEntry] = []
    cumulative_interest = Decimal("0")
    cumulative_principal = Decimal("0")

    for month in range(1, tenure_months + 1):
        if balance <= 0:
            break

        interest = (balance * r).quantize(PAISA, ROUND_HALF_UP)
        principal_portion = emi - interest

        # Handle final month where balance might be less than EMI
        if principal_portion > balance:
            principal_portion = balance
            emi_this_month = principal_portion + interest
        else:
            emi_this_month = emi

        balance -= principal_portion

        # Apply prepayments
        prepayment = monthly_prepayment + lump_sums.get(month, Decimal("0"))
        if prepayment > 0:
            actual_prepayment = min(prepayment, balance)
            balance -= actual_prepayment
        else:
            actual_prepayment = Decimal("0")

        cumulative_interest += interest
        cumulative_principal += principal_portion + actual_prepayment

        schedule.append(AmortizationEntry(
            month=month,
            emi=emi_this_month,
            principal=principal_portion,
            interest=interest,
            balance=max(balance, Decimal("0")),
            prepayment=actual_prepayment,
            cumulative_interest=cumulative_interest,
            cumulative_principal=cumulative_principal,
        ))

        if balance <= 0:
            break

    return schedule


def calculate_total_interest(
    principal: Decimal,
    annual_rate: Decimal,
    tenure_months: int,
) -> Decimal:
    """Calculate total interest paid over loan lifetime (no prepayments)."""
    emi = calculate_emi(principal, annual_rate, tenure_months)
    total_paid = emi * tenure_months
    return (total_paid - principal).quantize(PAISA, ROUND_HALF_UP)


def calculate_interest_saved(
    principal: Decimal,
    annual_rate: Decimal,
    tenure_months: int,
    monthly_prepayment: Decimal = Decimal("0"),
    lump_sums: dict[int, Decimal] | None = None,
) -> tuple[Decimal, int]:
    """Calculate interest saved and months saved with prepayments.

    Returns:
        (interest_saved, months_saved)
    """
    baseline_interest = calculate_total_interest(principal, annual_rate, tenure_months)

    schedule = generate_amortization(
        principal, annual_rate, tenure_months, monthly_prepayment, lump_sums
    )

    if not schedule:
        return Decimal("0"), 0

    actual_interest = schedule[-1].cumulative_interest
    months_taken = len(schedule)

    return (
        (baseline_interest - actual_interest).quantize(PAISA, ROUND_HALF_UP),
        tenure_months - months_taken,
    )


def reverse_emi_rate(
    principal: Decimal,
    emi: Decimal,
    tenure_months: int,
    precision: Decimal = Decimal("0.01"),
) -> Decimal:
    """Find interest rate that produces the given EMI (binary search).

    "I can pay ₹22,000/month for 5 years on ₹10L — what rate is that?"
    """
    low = Decimal("0.01")
    high = Decimal("50.0")

    for _ in range(100):  # Max iterations
        mid = (low + high) / 2
        calc_emi = calculate_emi(principal, mid, tenure_months)

        if abs(calc_emi - emi) <= precision:
            return mid.quantize(Decimal("0.01"), ROUND_HALF_UP)

        if calc_emi < emi:
            low = mid
        else:
            high = mid

    return mid.quantize(Decimal("0.01"), ROUND_HALF_UP)


def reverse_emi_tenure(
    principal: Decimal,
    emi: Decimal,
    annual_rate: Decimal,
) -> int:
    """Find tenure for given EMI and rate.

    "At 8.5% on ₹50L, how many months for ₹50,000 EMI?"
    """
    if annual_rate == 0:
        if emi <= 0:
            return 0
        return int((principal / emi).to_integral_value())

    r = annual_rate / Decimal("1200")

    # From EMI formula: n = log(EMI / (EMI - P*r)) / log(1 + r)
    denominator = emi - principal * r
    if denominator <= 0:
        return 0  # EMI too small to ever pay off

    # NOTE: Intentional precision tradeoff — Decimal→float for math.log().
    # Acceptable here because the result is rounded to an integer month count.
    import math
    n = math.log(float(emi / denominator)) / math.log(float(1 + r))
    return max(1, round(n))


def calculate_affordability(
    emi: Decimal,
    annual_rate: Decimal,
    tenure_months: int,
) -> Decimal:
    """Calculate max borrowable amount for given EMI budget.

    "I can pay ₹30,000/month at 9% for 20 years — how much can I borrow?"
    P = EMI * ((1+r)^n - 1) / (r * (1+r)^n)
    """
    if emi <= 0 or tenure_months <= 0:
        return Decimal("0")
    if annual_rate == 0:
        return (emi * tenure_months).quantize(PAISA, ROUND_HALF_UP)

    r = annual_rate / Decimal("1200")
    n = tenure_months
    factor = (1 + r) ** n
    principal = emi * (factor - 1) / (r * factor)
    return principal.quantize(PAISA, ROUND_HALF_UP)
