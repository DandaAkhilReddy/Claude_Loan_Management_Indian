"""Country-aware rules dispatcher.

Routes tax, deduction, and bank lookups to the correct country module.
Currently supports:
- IN (India) -> indian_rules
- US (United States) -> usa_rules
"""

from decimal import Decimal

from app.core import indian_rules, usa_rules


SUPPORTED_COUNTRIES = {"IN", "US"}


def _validate_country(country: str) -> str:
    """Normalize and validate country code."""
    code = country.upper().strip()
    if code not in SUPPORTED_COUNTRIES:
        raise ValueError(
            f"Unsupported country '{country}'. "
            f"Must be one of: {', '.join(sorted(SUPPORTED_COUNTRIES))}"
        )
    return code


# ---------- Tax Bracket ----------

def get_tax_bracket(
    country: str,
    annual_income: Decimal,
    **kwargs,
) -> Decimal:
    """Get marginal tax bracket for a given income.

    Args:
        country: 'IN' or 'US'.
        annual_income: Gross annual income in local currency.
        **kwargs:
            India: regime='old'|'new'
            US: filing_status='single'|'married_jointly'|
                'married_separately'|'head_of_household'

    Returns:
        Marginal tax rate as a Decimal.
    """
    code = _validate_country(country)

    if code == "IN":
        regime = kwargs.get("regime", "old")
        return indian_rules.get_user_tax_bracket(annual_income, regime)

    # US
    filing_status = kwargs.get("filing_status", "single")
    return usa_rules.get_us_tax_bracket(annual_income, filing_status)


# ---------- Loan Deductions ----------

def get_loan_deductions(
    country: str,
    loans: list,
    **kwargs,
) -> dict[str, Decimal]:
    """Calculate loan-related tax deductions.

    Args:
        country: 'IN' or 'US'.
        loans: List of LoanTaxInfo (IN) or USLoanTaxInfo (US) objects.
        **kwargs:
            India: regime='old'|'new'
            US: filing_status='single'|...

    Returns:
        Dict with category-wise deductions.
    """
    code = _validate_country(country)

    if code == "IN":
        regime = kwargs.get("regime", "old")
        return indian_rules.calculate_loan_deductions(loans, regime)

    # US
    filing_status = kwargs.get("filing_status", "single")
    return usa_rules.calculate_us_loan_deductions(loans, filing_status)


# ---------- Tax Options Comparison ----------

def compare_tax_options(
    country: str,
    annual_income: Decimal,
    loans: list,
    **kwargs,
) -> dict:
    """Compare tax-saving strategies for a country.

    India: Old vs New regime.
    US: Standard vs Itemized deduction.

    Args:
        country: 'IN' or 'US'.
        annual_income: Gross annual income in local currency.
        loans: List of country-appropriate LoanTaxInfo objects.
        **kwargs:
            US: filing_status, other_itemized_deductions

    Returns:
        Comparison dict with recommendation.
    """
    code = _validate_country(country)

    if code == "IN":
        return indian_rules.compare_tax_regimes(annual_income, loans)

    # US
    filing_status = kwargs.get("filing_status", "single")
    other_itemized = kwargs.get("other_itemized_deductions", Decimal("0"))
    return usa_rules.compare_standard_vs_itemized(
        annual_income, loans, filing_status, other_itemized
    )


# ---------- Bank Constants ----------

def get_banks(country: str) -> dict:
    """Get bank constants for a country.

    Args:
        country: 'IN' or 'US'.

    Returns:
        Dict of bank_code -> {full_name, ifsc_prefix/routing_prefix}.
    """
    code = _validate_country(country)

    if code == "IN":
        return indian_rules.INDIAN_BANKS

    return usa_rules.US_BANKS


# ---------- Loan Types ----------

def get_loan_types(country: str) -> list[str]:
    """Get supported loan types for a country.

    Args:
        country: 'IN' or 'US'.

    Returns:
        List of loan type strings.
    """
    code = _validate_country(country)

    if code == "IN":
        return indian_rules.LOAN_TYPES

    return usa_rules.US_LOAN_TYPES
