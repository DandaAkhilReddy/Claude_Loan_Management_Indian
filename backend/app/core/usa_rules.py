"""US tax rules, loan regulations, and bank constants.

Covers:
- Federal income tax brackets (2024)
- Standard vs itemized deduction comparison
- Mortgage interest deduction ($750K cap)
- Student loan interest deduction ($2,500 cap)
- US bank constants
"""

from decimal import Decimal
from dataclasses import dataclass


# ---------- Filing Statuses ----------

FILING_STATUSES = ["single", "married_jointly", "married_separately", "head_of_household"]


# ---------- Federal Income Tax Brackets (2024) ----------

US_TAX_BRACKETS: dict[str, list[tuple[Decimal, Decimal]]] = {
    "single": [
        (Decimal("11600"), Decimal("0.10")),
        (Decimal("47150"), Decimal("0.12")),
        (Decimal("100525"), Decimal("0.22")),
        (Decimal("191950"), Decimal("0.24")),
        (Decimal("243725"), Decimal("0.32")),
        (Decimal("609350"), Decimal("0.35")),
        (Decimal("99999999"), Decimal("0.37")),
    ],
    "married_jointly": [
        (Decimal("23200"), Decimal("0.10")),
        (Decimal("94300"), Decimal("0.12")),
        (Decimal("201050"), Decimal("0.22")),
        (Decimal("383900"), Decimal("0.24")),
        (Decimal("487450"), Decimal("0.32")),
        (Decimal("731200"), Decimal("0.35")),
        (Decimal("99999999"), Decimal("0.37")),
    ],
    "married_separately": [
        (Decimal("11600"), Decimal("0.10")),
        (Decimal("47150"), Decimal("0.12")),
        (Decimal("100525"), Decimal("0.22")),
        (Decimal("191950"), Decimal("0.24")),
        (Decimal("243725"), Decimal("0.32")),
        (Decimal("365600"), Decimal("0.35")),
        (Decimal("99999999"), Decimal("0.37")),
    ],
    "head_of_household": [
        (Decimal("16550"), Decimal("0.10")),
        (Decimal("63100"), Decimal("0.12")),
        (Decimal("100500"), Decimal("0.22")),
        (Decimal("191950"), Decimal("0.24")),
        (Decimal("243700"), Decimal("0.32")),
        (Decimal("609350"), Decimal("0.35")),
        (Decimal("99999999"), Decimal("0.37")),
    ],
}


# ---------- Standard Deduction Amounts (2024) ----------

STANDARD_DEDUCTION: dict[str, Decimal] = {
    "single": Decimal("14600"),
    "married_jointly": Decimal("29200"),
    "married_separately": Decimal("14600"),
    "head_of_household": Decimal("21900"),
}


# ---------- Loan-Related Deduction Limits ----------

MORTGAGE_INTEREST_DEDUCTION_LIMIT = Decimal("750000")  # Loan principal cap
STUDENT_LOAN_INTEREST_DEDUCTION_LIMIT = Decimal("2500")

# SALT (State and Local Tax) deduction cap for itemizing
SALT_DEDUCTION_LIMIT = Decimal("10000")

# Student loan interest deduction income phase-out (single filer, 2024)
STUDENT_LOAN_MAGI_PHASEOUT_SINGLE = (Decimal("80000"), Decimal("95000"))
STUDENT_LOAN_MAGI_PHASEOUT_JOINT = (Decimal("165000"), Decimal("195000"))


# ---------- Loan Tax Info Dataclass ----------

@dataclass
class USLoanTaxInfo:
    """Tax-relevant info about a US loan."""
    loan_type: str
    annual_interest_paid: Decimal
    annual_principal_paid: Decimal
    eligible_mortgage_deduction: bool = False
    eligible_student_loan_deduction: bool = False
    outstanding_principal: Decimal = Decimal("0")  # For mortgage cap calculation


# ---------- Tax Calculation Functions ----------

def calculate_us_tax(
    income: Decimal,
    filing_status: str = "single",
) -> Decimal:
    """Calculate federal income tax using progressive bracket rates.

    Args:
        income: Taxable income after deductions.
        filing_status: One of 'single', 'married_jointly',
                       'married_separately', 'head_of_household'.

    Returns:
        Total federal income tax owed.
    """
    if filing_status not in US_TAX_BRACKETS:
        raise ValueError(
            f"Invalid filing status '{filing_status}'. "
            f"Must be one of: {', '.join(FILING_STATUSES)}"
        )

    slabs = US_TAX_BRACKETS[filing_status]
    tax = Decimal("0")
    prev_limit = Decimal("0")

    for limit, rate in slabs:
        if income <= prev_limit:
            break
        taxable = min(income, limit) - prev_limit
        tax += taxable * rate
        prev_limit = limit

    return tax.quantize(Decimal("0.01"))


def calculate_us_loan_deductions(
    loans: list[USLoanTaxInfo],
    filing_status: str = "single",
) -> dict[str, Decimal]:
    """Calculate total itemizable deductions from loans.

    Mortgage interest: deductible on first $750K of loan principal.
    Student loan interest: up to $2,500 (above-the-line, not itemized).

    Args:
        loans: List of USLoanTaxInfo objects.
        filing_status: Filing status for phase-out calculations.

    Returns:
        Dict with category-wise deductions and totals.
    """
    deductions: dict[str, Decimal] = {
        "mortgage_interest": Decimal("0"),
        "student_loan_interest": Decimal("0"),
        "total_itemizable": Decimal("0"),
        "total_above_the_line": Decimal("0"),
    }

    total_mortgage_interest = Decimal("0")
    total_student_loan_interest = Decimal("0")

    for loan in loans:
        if loan.eligible_mortgage_deduction:
            # Prorate deduction if outstanding principal exceeds cap
            if loan.outstanding_principal > MORTGAGE_INTEREST_DEDUCTION_LIMIT:
                ratio = MORTGAGE_INTEREST_DEDUCTION_LIMIT / loan.outstanding_principal
                deductible = loan.annual_interest_paid * ratio
            else:
                deductible = loan.annual_interest_paid
            total_mortgage_interest += deductible

        if loan.eligible_student_loan_deduction:
            total_student_loan_interest += loan.annual_interest_paid

    # Apply student loan interest cap
    deductions["student_loan_interest"] = min(
        total_student_loan_interest, STUDENT_LOAN_INTEREST_DEDUCTION_LIMIT
    )
    deductions["mortgage_interest"] = total_mortgage_interest

    # Mortgage interest is an itemized deduction
    deductions["total_itemizable"] = deductions["mortgage_interest"]

    # Student loan interest is above-the-line (taken regardless of
    # standard vs itemized)
    deductions["total_above_the_line"] = deductions["student_loan_interest"]

    return deductions


def compare_standard_vs_itemized(
    annual_income: Decimal,
    loans: list[USLoanTaxInfo],
    filing_status: str = "single",
    other_itemized_deductions: Decimal = Decimal("0"),
) -> dict:
    """Compare standard deduction vs itemizing with loan deductions.

    Student loan interest ($2,500 cap) is an above-the-line deduction,
    so it applies in BOTH scenarios.

    Args:
        annual_income: Gross annual income.
        loans: List of USLoanTaxInfo objects.
        filing_status: Filing status.
        other_itemized_deductions: Non-loan itemized deductions (SALT,
                                   charitable, medical, etc.).

    Returns:
        Comparison dict with taxes under each approach and recommendation.
    """
    if filing_status not in STANDARD_DEDUCTION:
        raise ValueError(
            f"Invalid filing status '{filing_status}'. "
            f"Must be one of: {', '.join(FILING_STATUSES)}"
        )

    loan_deductions = calculate_us_loan_deductions(loans, filing_status)
    above_the_line = loan_deductions["total_above_the_line"]

    # Income after above-the-line deductions (applies in both scenarios)
    adjusted_income = max(Decimal("0"), annual_income - above_the_line)

    # Standard deduction scenario
    std_deduction = STANDARD_DEDUCTION[filing_status]
    std_taxable = max(Decimal("0"), adjusted_income - std_deduction)
    std_tax = calculate_us_tax(std_taxable, filing_status)

    # Itemized deduction scenario
    total_itemized = loan_deductions["total_itemizable"] + other_itemized_deductions
    item_taxable = max(Decimal("0"), adjusted_income - total_itemized)
    item_tax = calculate_us_tax(item_taxable, filing_status)

    recommended = "standard" if std_tax <= item_tax else "itemized"
    savings = abs(std_tax - item_tax)

    return {
        "standard": {
            "deduction_amount": std_deduction,
            "above_the_line": above_the_line,
            "taxable_income": std_taxable,
            "tax": std_tax,
        },
        "itemized": {
            "deduction_amount": total_itemized,
            "above_the_line": above_the_line,
            "mortgage_interest": loan_deductions["mortgage_interest"],
            "other_deductions": other_itemized_deductions,
            "taxable_income": item_taxable,
            "tax": item_tax,
        },
        "recommended": recommended,
        "savings": savings,
        "explanation": (
            f"{'Standard' if recommended == 'standard' else 'Itemized'} deduction "
            f"saves you ${savings:,.0f}. "
            + (
                f"Your itemized deductions (${total_itemized:,.0f}) are "
                f"{'below' if recommended == 'standard' else 'above'} the "
                f"standard deduction (${std_deduction:,.0f})."
            )
        ),
    }


def get_us_tax_bracket(
    annual_income: Decimal,
    filing_status: str = "single",
) -> Decimal:
    """Get marginal tax bracket for a given income and filing status.

    Args:
        annual_income: Gross annual income.
        filing_status: Filing status.

    Returns:
        Marginal tax rate as a Decimal (e.g. Decimal("0.22")).
    """
    if filing_status not in US_TAX_BRACKETS:
        raise ValueError(
            f"Invalid filing status '{filing_status}'. "
            f"Must be one of: {', '.join(FILING_STATUSES)}"
        )

    slabs = US_TAX_BRACKETS[filing_status]
    bracket = Decimal("0")
    prev_limit = Decimal("0")

    for limit, rate in slabs:
        if annual_income > prev_limit:
            bracket = rate
        prev_limit = limit

    return bracket


# ---------- US Bank Constants ----------

US_BANKS = {
    "CHASE": {"full_name": "JPMorgan Chase", "routing_prefix": "0210"},
    "BOA": {"full_name": "Bank of America", "routing_prefix": "0260"},
    "WELLS": {"full_name": "Wells Fargo", "routing_prefix": "1210"},
    "CITI": {"full_name": "Citibank", "routing_prefix": "0219"},
    "USB": {"full_name": "U.S. Bank", "routing_prefix": "0917"},
    "PNC": {"full_name": "PNC Financial Services", "routing_prefix": "0430"},
    "CAPONE": {"full_name": "Capital One", "routing_prefix": "0550"},
    "TD": {"full_name": "TD Bank", "routing_prefix": "0311"},
    "ALLY": {"full_name": "Ally Financial", "routing_prefix": "1240"},
    "SOFI": {"full_name": "SoFi", "routing_prefix": None},
}

US_LOAN_TYPES = ["home", "personal", "car", "education", "business", "credit_card"]

RATE_TYPES = ["fixed", "variable", "hybrid"]
