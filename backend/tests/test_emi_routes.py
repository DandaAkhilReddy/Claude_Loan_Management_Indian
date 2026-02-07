"""Tests for /api/emi/* routes — public, no auth required."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_calculate_emi(async_client: AsyncClient):
    """POST /api/emi/calculate with standard home loan params returns valid EMI."""
    resp = await async_client.post("/api/emi/calculate", json={
        "principal": 5000000,
        "annual_rate": 8.5,
        "tenure_months": 240,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["emi"]) > 0
    assert float(data["total_interest"]) > 0
    assert float(data["total_payment"]) > float(data["total_interest"])
    assert data["interest_saved"] == "0"
    assert data["months_saved"] == 0


@pytest.mark.asyncio
async def test_calculate_emi_with_prepayment(async_client: AsyncClient):
    """POST /api/emi/calculate with monthly_prepayment yields interest savings."""
    resp = await async_client.post("/api/emi/calculate", json={
        "principal": 5000000,
        "annual_rate": 8.5,
        "tenure_months": 240,
        "monthly_prepayment": 5000,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["emi"]) > 0
    assert float(data["interest_saved"]) > 0
    assert data["months_saved"] > 0


@pytest.mark.asyncio
async def test_calculate_emi_zero_rate(async_client: AsyncClient):
    """Zero interest rate: EMI should equal principal / tenure."""
    resp = await async_client.post("/api/emi/calculate", json={
        "principal": 2400000,
        "annual_rate": 0,
        "tenure_months": 240,
    })
    assert resp.status_code == 200
    data = resp.json()
    emi = float(data["emi"])
    # principal / tenure = 2400000 / 240 = 10000.0
    assert abs(emi - 10000.0) < 0.01


@pytest.mark.asyncio
async def test_reverse_calculate(async_client: AsyncClient):
    """POST /api/emi/reverse-calculate finds rate ~8.5% for known EMI."""
    resp = await async_client.post("/api/emi/reverse-calculate", json={
        "principal": 5000000,
        "target_emi": 43391,
        "tenure_months": 240,
    })
    assert resp.status_code == 200
    data = resp.json()
    estimated_rate = float(data["estimated_rate"])
    # Should be close to 8.5%
    assert 8.0 <= estimated_rate <= 9.0


@pytest.mark.asyncio
async def test_affordability(async_client: AsyncClient):
    """POST /api/emi/affordability returns a positive max principal."""
    resp = await async_client.post("/api/emi/affordability", json={
        "monthly_emi_budget": 50000,
        "annual_rate": 8.5,
        "tenure_months": 240,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["max_principal"]) > 0
    assert float(data["total_interest"]) > 0
    assert float(data["total_payment"]) > float(data["max_principal"])


@pytest.mark.asyncio
async def test_emi_validation_error(async_client: AsyncClient):
    """Negative principal should trigger 422 validation error."""
    resp = await async_client.post("/api/emi/calculate", json={
        "principal": -1000,
        "annual_rate": 8.5,
        "tenure_months": 240,
    })
    assert resp.status_code == 422
