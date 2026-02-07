"""Tests for /api/scanner/* routes — all require auth."""

import uuid
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

MOCK_JOB_ID = uuid.UUID("00000000-0000-4000-a000-000000000030")


@pytest.mark.asyncio
async def test_upload_invalid_type(async_client: AsyncClient):
    """POST /api/scanner/upload with unsupported content_type returns 400."""
    # Create a fake file with disallowed MIME type
    resp = await async_client.post(
        "/api/scanner/upload",
        headers={"Authorization": "Bearer token"},
        files={"file": ("malware.exe", b"fake content", "application/exe")},
    )
    assert resp.status_code == 400
    assert "not supported" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_scan_status_not_found(async_client: AsyncClient):
    """GET /api/scanner/status/{uuid} returns 404 when job not found."""
    with patch("app.api.routes.scanner.ScanJobRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        MockRepo.return_value = mock_repo

        resp = await async_client.get(
            f"/api/scanner/status/{MOCK_JOB_ID}",
            headers={"Authorization": "Bearer token"},
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Scan job not found"


@pytest.mark.asyncio
async def test_confirm_scan_not_found(async_client: AsyncClient):
    """POST /api/scanner/{uuid}/confirm returns 404 when job not found."""
    with patch("app.api.routes.scanner.ScanJobRepository") as MockRepo:
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        MockRepo.return_value = mock_repo

        resp = await async_client.post(
            f"/api/scanner/{MOCK_JOB_ID}/confirm",
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
            },
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Scan job not found"
