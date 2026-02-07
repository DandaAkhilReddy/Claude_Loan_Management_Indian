"""Tests for /api/optimizer/* routes — all require auth."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.db.models import Loan, RepaymentPlan
from tests.conftest import MOCK_USER_ID

MOCK_LOAN_ID = uuid.UUID("00000000-0000-4000-a000-000000000010")
MOCK_PLAN_ID = uuid.UUID("00000000-0000-4000-a000-000000000020")


def _make_mock_loan(**overrides) -> MagicMock:
    """Create a mock Loan ORM object for optimizer tests."""
    loan = MagicMock(spec=Loan)
    defaults = dict(
        id=MOCK_LOAN_ID,
        user_id=MOCK_USER_ID,
        bank_name="SBI",
        loan_type="home",
        principal_amount=5000000.0,
        outstanding_principal=4500000.0,
        interest_rate=8.5,
        interest_rate_type="floating",
        tenure_months=240,
        remaining_tenure_months=220,
        emi_amount=43391.0,
        emi_due_date=5,
        prepayment_penalty_pct=0.0,
        foreclosure_charges_pct=0.0,
        eligible_80c=True,
        eligible_24b=True,
        eligible_80e=False,
        eligible_80eea=False,
        disbursement_date=None,
        status="active",
        source="manual",
        source_scan_id=None,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(loan, k, v)
    return loan


@pytest.mark.asyncio
async def test_quick_compare(async_client: AsyncClient):
    """POST /api/optimizer/quick-compare returns savings preview."""
    mock_loan = _make_mock_loan()

    with patch("app.api.routes.optimizer.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.list_by_user = AsyncMock(return_value=[mock_loan])
        MockRepo.return_value = mock_repo

        resp = await async_client.post(
            "/api/optimizer/quick-compare",
            headers={"Authorization": "Bearer token"},
            json={
                "loan_ids": [str(MOCK_LOAN_ID)],
                "monthly_extra": 10000,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "interest_saved" in data
    assert "months_saved" in data
    assert "debt_free_months" in data


@pytest.mark.asyncio
async def test_what_if(async_client: AsyncClient):
    """POST /api/optimizer/what-if returns interest and months comparison."""
    mock_loan = _make_mock_loan()

    with patch("app.api.routes.optimizer.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_loan)
        MockRepo.return_value = mock_repo

        resp = await async_client.post(
            "/api/optimizer/what-if",
            headers={"Authorization": "Bearer token"},
            json={
                "loan_id": str(MOCK_LOAN_ID),
                "monthly_extra": 5000,
                "lump_sum": 100000,
                "lump_sum_month": 6,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "original_interest" in data
    assert "new_interest" in data
    assert "interest_saved" in data
    assert "original_months" in data
    assert "new_months" in data
    assert "months_saved" in data
    assert float(data["interest_saved"]) >= 0


@pytest.mark.asyncio
async def test_save_plan(async_client: AsyncClient):
    """POST /api/optimizer/save-plan persists a repayment plan."""
    mock_plan = MagicMock(spec=RepaymentPlan)
    mock_plan.id = MOCK_PLAN_ID

    with patch("app.api.routes.optimizer.RepaymentPlanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_plan)
        MockRepo.return_value = mock_repo

        resp = await async_client.post(
            "/api/optimizer/save-plan",
            headers={"Authorization": "Bearer token"},
            json={
                "name": "My Avalanche Plan",
                "strategy": "avalanche",
                "config": {"monthly_extra": 10000},
                "results": {"interest_saved": 500000, "months_saved": 24},
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["plan_id"] == str(MOCK_PLAN_ID)
    assert data["message"] == "Plan saved"


@pytest.mark.asyncio
async def test_list_plans(async_client: AsyncClient):
    """GET /api/optimizer/plans returns empty list when no plans exist."""
    with patch("app.api.routes.optimizer.RepaymentPlanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.list_by_user = AsyncMock(return_value=[])
        MockRepo.return_value = mock_repo

        resp = await async_client.get(
            "/api/optimizer/plans",
            headers={"Authorization": "Bearer token"},
        )

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_tax_impact(async_client: AsyncClient):
    """POST /api/optimizer/tax-impact returns tax regime comparison."""
    mock_loan = _make_mock_loan()

    with patch("app.api.routes.optimizer.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.list_by_user = AsyncMock(return_value=[mock_loan])
        MockRepo.return_value = mock_repo

        resp = await async_client.post(
            "/api/optimizer/tax-impact",
            headers={"Authorization": "Bearer token"},
            json={"annual_income": 1500000},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "old_regime_tax" in data
    assert "new_regime_tax" in data
    assert "recommended" in data
    assert data["recommended"] in ("old", "new")
    assert "savings" in data
    assert "explanation" in data
    assert "deductions" in data
