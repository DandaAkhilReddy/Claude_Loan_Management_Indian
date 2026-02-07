"""Tests for /api/loans/* routes — all require auth."""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.db.models import Loan
from tests.conftest import MOCK_USER_ID

MOCK_LOAN_ID = uuid.UUID("00000000-0000-4000-a000-000000000010")


def _make_mock_loan(**overrides) -> MagicMock:
    """Create a mock Loan ORM object with all required fields."""
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
async def test_list_loans_empty(async_client: AsyncClient):
    """GET /api/loans returns empty list when user has no loans."""
    with patch("app.api.routes.loans.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.list_by_user = AsyncMock(return_value=[])
        MockRepo.return_value = mock_repo

        resp = await async_client.get(
            "/api/loans",
            headers={"Authorization": "Bearer token"},
        )

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_loan(async_client: AsyncClient):
    """POST /api/loans creates a loan and returns 201."""
    mock_loan = _make_mock_loan()

    with patch("app.api.routes.loans.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_loan)
        MockRepo.return_value = mock_repo

        resp = await async_client.post(
            "/api/loans",
            headers={"Authorization": "Bearer token"},
            json={
                "bank_name": "SBI",
                "loan_type": "home",
                "principal_amount": 5000000,
                "outstanding_principal": 4500000,
                "interest_rate": 8.5,
                "interest_rate_type": "floating",
                "tenure_months": 240,
                "remaining_tenure_months": 220,
                "emi_amount": 43391,
                "emi_due_date": 5,
                "eligible_80c": True,
                "eligible_24b": True,
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["bank_name"] == "SBI"
    assert data["loan_type"] == "home"
    assert data["id"] == str(MOCK_LOAN_ID)


@pytest.mark.asyncio
async def test_get_loan(async_client: AsyncClient):
    """GET /api/loans/{id} returns the loan when found."""
    mock_loan = _make_mock_loan()

    with patch("app.api.routes.loans.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_loan)
        MockRepo.return_value = mock_repo

        resp = await async_client.get(
            f"/api/loans/{MOCK_LOAN_ID}",
            headers={"Authorization": "Bearer token"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(MOCK_LOAN_ID)
    assert data["bank_name"] == "SBI"


@pytest.mark.asyncio
async def test_get_loan_not_found(async_client: AsyncClient):
    """GET /api/loans/{id} returns 404 when loan not found."""
    with patch("app.api.routes.loans.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        MockRepo.return_value = mock_repo

        resp = await async_client.get(
            f"/api/loans/{MOCK_LOAN_ID}",
            headers={"Authorization": "Bearer token"},
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Loan not found"


@pytest.mark.asyncio
async def test_update_loan(async_client: AsyncClient):
    """PUT /api/loans/{id} updates and returns the loan."""
    mock_loan = _make_mock_loan(outstanding_principal=4000000.0)

    with patch("app.api.routes.loans.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.update = AsyncMock(return_value=mock_loan)
        MockRepo.return_value = mock_repo

        resp = await async_client.put(
            f"/api/loans/{MOCK_LOAN_ID}",
            headers={"Authorization": "Bearer token"},
            json={"outstanding_principal": 4000000},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(MOCK_LOAN_ID)


@pytest.mark.asyncio
async def test_delete_loan(async_client: AsyncClient):
    """DELETE /api/loans/{id} returns success message when loan exists."""
    with patch("app.api.routes.loans.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.delete = AsyncMock(return_value=True)
        MockRepo.return_value = mock_repo

        resp = await async_client.delete(
            f"/api/loans/{MOCK_LOAN_ID}",
            headers={"Authorization": "Bearer token"},
        )

    assert resp.status_code == 200
    assert resp.json()["message"] == "Loan deleted"


@pytest.mark.asyncio
async def test_delete_loan_not_found(async_client: AsyncClient):
    """DELETE /api/loans/{id} returns 404 when loan does not exist."""
    with patch("app.api.routes.loans.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.delete = AsyncMock(return_value=False)
        MockRepo.return_value = mock_repo

        resp = await async_client.delete(
            f"/api/loans/{MOCK_LOAN_ID}",
            headers={"Authorization": "Bearer token"},
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Loan not found"


@pytest.mark.asyncio
async def test_get_amortization(async_client: AsyncClient):
    """GET /api/loans/{id}/amortization returns schedule with entries."""
    mock_loan = _make_mock_loan()

    with patch("app.api.routes.loans.LoanRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_loan)
        MockRepo.return_value = mock_repo

        resp = await async_client.get(
            f"/api/loans/{MOCK_LOAN_ID}/amortization",
            headers={"Authorization": "Bearer token"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "schedule" in data
    assert len(data["schedule"]) > 0
    assert "loan_id" in data
    assert data["loan_id"] == str(MOCK_LOAN_ID)
    # Check first entry has expected fields
    first = data["schedule"][0]
    assert "month" in first
    assert "emi" in first
    assert "principal" in first
    assert "interest" in first
    assert "balance" in first
