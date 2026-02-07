"""Indian tax rules, RBI regulations, and bank constants.

Covers:
- RBI prepayment rules (2014 circular: 0% penalty on floating rate)
- Foreclosure charges matrix by loan type
- Income tax deductions: 80C, 24(b), 80E, 80EEA
- Old vs New regime comparison
- Indian bank constants
"""

from decimal import Decimal
from dataclasses import dataclass


# ---------- RBI Prepayment Rules (2014 Circular) ----------

FLOATING_RATE_PREPAYMENT_PENALTY = Decimal("0")  # RBI mandates 0% for floating

FORECLOSURE_CHARGES = {
    "home": {"floating": Decimal("0"), "fixed": Decimal("2.0"), "hybrid": Decimal("1.5")},
    "personal": {"floating": Decimal("2.0"), "fixed": Decimal("4.0"), "hybrid": Decimal("3.0")},
    "car": {"floating": Decimal("0"), "fixed": Decimal("5.0"), "hybrid": Decimal("2.5")},
    "education": {"floating": Decimal("0"), "fixed": Decimal("1.0"), "hybrid": Decimal("0.5")},
    "gold": {"floating": Decimal("0.5"), "fixed": Decimal("1.0"), "hybrid": Decimal("0.5")},
    "credit_card": {"floating": Decimal("0"), "fixed": Decimal("0"), "hybrid": Decimal("0")},
}


def get_prepayment_penalty(loan_type: str, rate_type: str) -> Decimal:
    """Get prepayment penalty percentage based on loan and rate type."""
    if rate_type == "floating":
        return FLOATING_RATE_PREPAYMENT_PENALTY
    charges = FORECLOSURE_CHARGES.get(loan_type, {})
    return charges.get(rate_type, Decimal("2.0"))


# ---------- Income Tax Deductions ----------

@dataclass
class TaxDeductionLimits:
    """Annual limits for Indian income tax deductions."""
    section_80c_limit: Decimal = Decimal("150000")       # ₹1.5L (principal repayment)
    section_24b_self_occupied: Decimal = Decimal("200000")  # ₹2L (home loan interest)
    section_24b_let_out: Decimal = Decimal("0")             # No limit for let-out
    section_80e_limit: Decimal = Decimal("0")               # No cap (8-year window)
    section_80eea_limit: Decimal = Decimal("150000")        # ₹1.5L (first-time buyer, 2019-2022)


OLD_REGIME_LIMITS = TaxDeductionLimits()

# Tax slabs (FY 2024-25)
OLD_REGIME_SLABS = [
    (Decimal("250000"), Decimal("0")),
    (Decimal("500000"), Decimal("0.05")),
    (Decimal("1000000"), Decimal("0.20")),
    (Decimal("99999999"), Decimal("0.30")),
]

NEW_REGIME_SLABS = [
    (Decimal("300000"), Decimal("0")),
    (Decimal("700000"), Decimal("0.05")),
    (Decimal("1000000"), Decimal("0.10")),
    (Decimal("1200000"), Decimal("0.15")),
    (Decimal("1500000"), Decimal("0.20")),
    (Decimal("99999999"), Decimal("0.30")),
]


@dataclass
class LoanTaxInfo:
    """Tax-relevant info about a loan."""
    loan_type: str
    annual_interest_paid: Decimal
    annual_principal_paid: Decimal
    eligible_80c: bool = False
    eligible_24b: bool = False
    eligible_80e: bool = False
    eligible_80eea: bool = False
    is_self_occupied: bool = True  # For 24(b) cap


def calculate_tax_for_slab(income: Decimal, slabs: list[tuple[Decimal, Decimal]]) -> Decimal:
    """Calculate income tax using progressive slab rates."""
    tax = Decimal("0")
    prev_limit = Decimal("0")

    for limit, rate in slabs:
        if income <= prev_limit:
            break
        taxable = min(income, limit) - prev_limit
        tax += taxable * rate
        prev_limit = limit

    return tax.quantize(Decimal("0.01"))


def calculate_loan_deductions(
    loans: list[LoanTaxInfo],
    regime: str = "old",
) -> dict[str, Decimal]:
    """Calculate total tax deductions from loans.

    Returns dict with section-wise deductions.
    """
    limits = OLD_REGIME_LIMITS

    deductions = {
        "80c": Decimal("0"),
        "24b": Decimal("0"),
        "80e": Decimal("0"),
        "80eea": Decimal("0"),
        "total": Decimal("0"),
    }

    if regime == "new":
        # New regime has very limited deductions
        return deductions

    total_80c = Decimal("0")
    total_24b = Decimal("0")
    total_80e = Decimal("0")
    total_80eea = Decimal("0")

    for loan in loans:
        if loan.eligible_80c:
            total_80c += loan.annual_principal_paid

        if loan.eligible_24b:
            cap = limits.section_24b_self_occupied if loan.is_self_occupied else loan.annual_interest_paid
            total_24b += min(loan.annual_interest_paid, cap)

        if loan.eligible_80e:
            total_80e += loan.annual_interest_paid  # No cap

        if loan.eligible_80eea:
            total_80eea += loan.annual_interest_paid

    deductions["80c"] = min(total_80c, limits.section_80c_limit)
    deductions["24b"] = min(total_24b, limits.section_24b_self_occupied)
    deductions["80e"] = total_80e  # No limit
    deductions["80eea"] = min(total_80eea, limits.section_80eea_limit)
    deductions["total"] = sum(v for k, v in deductions.items() if k != "total")

    return deductions


def compare_tax_regimes(
    annual_income: Decimal,
    loans: list[LoanTaxInfo],
) -> dict:
    """Compare old vs new tax regime considering loan deductions.

    Returns which regime saves more and by how much.
    """
    # Old regime
    old_deductions = calculate_loan_deductions(loans, "old")
    old_taxable = max(Decimal("0"), annual_income - old_deductions["total"])
    old_tax = calculate_tax_for_slab(old_taxable, OLD_REGIME_SLABS)

    # New regime (minimal loan deductions)
    new_deductions = calculate_loan_deductions(loans, "new")
    new_taxable = max(Decimal("0"), annual_income - new_deductions["total"])
    new_tax = calculate_tax_for_slab(new_taxable, NEW_REGIME_SLABS)

    # Standard deduction (₹50,000 in new regime, ₹50,000 in old)
    # Already factored into slabs for simplicity

    recommended = "old" if old_tax <= new_tax else "new"
    savings = abs(old_tax - new_tax)

    return {
        "old_regime": {
            "taxable_income": old_taxable,
            "tax": old_tax,
            "deductions": old_deductions,
        },
        "new_regime": {
            "taxable_income": new_taxable,
            "tax": new_tax,
            "deductions": new_deductions,
        },
        "recommended": recommended,
        "savings": savings,
        "explanation": (
            f"{'Old' if recommended == 'old' else 'New'} regime saves you "
            f"₹{savings:,.0f} because of your loan deductions"
        ),
    }


def get_user_tax_bracket(annual_income: Decimal, regime: str = "old") -> Decimal:
    """Get marginal tax bracket for a given income."""
    slabs = OLD_REGIME_SLABS if regime == "old" else NEW_REGIME_SLABS
    bracket = Decimal("0")
    prev_limit = Decimal("0")

    for limit, rate in slabs:
        if annual_income > prev_limit:
            bracket = rate
        prev_limit = limit

    return bracket


# ---------- Indian Bank Constants ----------

INDIAN_BANKS = {
    "SBI": {"full_name": "State Bank of India", "ifsc_prefix": "SBIN"},
    "HDFC": {"full_name": "HDFC Bank", "ifsc_prefix": "HDFC"},
    "ICICI": {"full_name": "ICICI Bank", "ifsc_prefix": "ICIC"},
    "AXIS": {"full_name": "Axis Bank", "ifsc_prefix": "UTIB"},
    "PNB": {"full_name": "Punjab National Bank", "ifsc_prefix": "PUNB"},
    "BOB": {"full_name": "Bank of Baroda", "ifsc_prefix": "BARB"},
    "KOTAK": {"full_name": "Kotak Mahindra Bank", "ifsc_prefix": "KKBK"},
    "CANARA": {"full_name": "Canara Bank", "ifsc_prefix": "CNRB"},
    "UNION": {"full_name": "Union Bank of India", "ifsc_prefix": "UBIN"},
    "IDBI": {"full_name": "IDBI Bank", "ifsc_prefix": "IBKL"},
    "BAJAJ": {"full_name": "Bajaj Finance", "ifsc_prefix": None},
    "TATA": {"full_name": "Tata Capital", "ifsc_prefix": None},
    "LIC_HFL": {"full_name": "LIC Housing Finance", "ifsc_prefix": None},
}

LOAN_TYPES = ["home", "personal", "car", "education", "gold", "credit_card"]

RATE_TYPES = ["floating", "fixed", "hybrid"]
