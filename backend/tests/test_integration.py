"""Integration tests for Indian Loan Analyzer API routes.

Tests cover: loan CRUD + optimizer flow, user isolation, tax impact,
data export, and health endpoints.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import Loan, RepaymentPlan, ScanJob

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
OTHER_LOAN_ID = uuid.UUID("00000000-0000-4000-a000-000000000099")


def _make_mock_loan(
    loan_id=None,
    loan_type="home",
    bank_name="SBI",
    principal=5000000.0,
    outstanding=4500000.0,
    rate=8.5,
    tenure=240,
    remaining=220,
    emi=43391.0,
    eligible_80c=True,
    eligible_24b=True,
    eligible_80e=False,
    eligible_80eea=False,
    eligible_mortgage_deduction=False,
    eligible_student_loan_deduction=False,
):
    """Create a mock Loan with all attributes the routes access."""
    loan = MagicMock(spec=Loan)
    loan.id = loan_id or uuid.UUID("00000000-0000-4000-a000-000000000010")
    loan.user_id = MOCK_USER_ID
    loan.bank_name = bank_name
    loan.loan_type = loan_type
    loan.principal_amount = principal
    loan.outstanding_principal = outstanding
    loan.interest_rate = rate
    loan.interest_rate_type = "floating"
    loan.tenure_months = tenure
    loan.remaining_tenure_months = remaining
    loan.emi_amount = emi
    loan.emi_due_date = 5
    loan.prepayment_penalty_pct = 0.0
    loan.foreclosure_charges_pct = 0.0
    loan.eligible_80c = eligible_80c
    loan.eligible_24b = eligible_24b
    loan.eligible_80e = eligible_80e
    loan.eligible_80eea = eligible_80eea
    loan.eligible_mortgage_deduction = eligible_mortgage_deduction
    loan.eligible_student_loan_deduction = eligible_student_loan_deduction
    loan.disbursement_date = None
    loan.status = "active"
    loan.source = "manual"
    loan.source_scan_id = None
    loan.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    loan.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return loan


def _make_mock_plan(plan_id=None, name="Test Plan", strategy="avalanche"):
    """Create a mock RepaymentPlan."""
    plan = MagicMock(spec=RepaymentPlan)
    plan.id = plan_id or uuid.uuid4()
    plan.user_id = MOCK_USER_ID
    plan.name = name
    plan.strategy = strategy
    plan.config = {"monthly_extra": 5000}
    plan.results = {"interest_saved": 100000}
    plan.is_active = False
    plan.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return plan


def _make_mock_scan(scan_id=None):
    """Create a mock ScanJob."""
    scan = MagicMock(spec=ScanJob)
    scan.id = scan_id or uuid.uuid4()
    scan.user_id = MOCK_USER_ID
    scan.original_filename = "loan_doc.pdf"
    scan.status = "completed"
    scan.extracted_fields = {"bank": "SBI"}
    scan.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return scan


# ===========================================================================
# TestLoanOptimizeFlow
# ===========================================================================

class TestLoanOptimizeFlow:
    """Tests for loan creation + optimizer endpoints working together."""

    @pytest.mark.asyncio
    async def test_create_loan_then_quick_compare(self, async_client, mock_loan):
        """Create a loan, then run quick-compare on it -> 200."""
        mock_loan.eligible_mortgage_deduction = False
        mock_loan.eligible_student_loan_deduction = False

        with patch("app.api.routes.loans.LoanRepository") as MockLoanRepo:
            repo_instance = AsyncMock()
            MockLoanRepo.return_value = repo_instance
            repo_instance.create.return_value = mock_loan

            create_resp = await async_client.post("/api/loans", json={
                "bank_name": "SBI",
                "loan_type": "home",
                "principal_amount": 5000000,
                "outstanding_principal": 4500000,
                "interest_rate": 8.5,
                "tenure_months": 240,
                "remaining_tenure_months": 220,
                "emi_amount": 43391,
                "eligible_80c": True,
                "eligible_24b": True,
            })
            assert create_resp.status_code == 201

        loan_id = str(mock_loan.id)

        with patch("app.api.routes.optimizer.LoanRepository") as MockOptRepo:
            repo_instance = AsyncMock()
            MockOptRepo.return_value = repo_instance
            repo_instance.list_by_user.return_value = [mock_loan]

            qc_resp = await async_client.post("/api/optimizer/quick-compare", json={
                "loan_ids": [loan_id],
                "monthly_extra": 5000,
            })
            assert qc_resp.status_code == 200
            data = qc_resp.json()
            assert "interest_saved" in data
            assert "months_saved" in data

    @pytest.mark.asyncio
    async def test_quick_compare_multiple_loans(self, async_client):
        """Quick-compare with two loans -> 200."""
        loan_a = _make_mock_loan(
            loan_id=uuid.UUID("00000000-0000-4000-a000-000000000011"),
            bank_name="SBI", loan_type="home", rate=8.5,
        )
        loan_b = _make_mock_loan(
            loan_id=uuid.UUID("00000000-0000-4000-a000-000000000012"),
            bank_name="HDFC", loan_type="personal", rate=12.0,
            principal=1000000, outstanding=900000, tenure=60,
            remaining=50, emi=22244,
            eligible_80c=False, eligible_24b=False,
        )

        with patch("app.api.routes.optimizer.LoanRepository") as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.list_by_user.return_value = [loan_a, loan_b]

            resp = await async_client.post("/api/optimizer/quick-compare", json={
                "loan_ids": [str(loan_a.id), str(loan_b.id)],
                "monthly_extra": 10000,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "interest_saved" in data
            assert "debt_free_months" in data

    @pytest.mark.asyncio
    async def test_what_if_monthly_extra(self, async_client, mock_loan):
        """What-if scenario with monthly extra -> 200 with savings data."""
        with patch("app.api.routes.optimizer.LoanRepository") as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.get_by_id.return_value = mock_loan

            resp = await async_client.post("/api/optimizer/what-if", json={
                "loan_id": str(mock_loan.id),
                "monthly_extra": 5000,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "interest_saved" in data
            assert "months_saved" in data
            assert "original_interest" in data
            assert "new_interest" in data
            assert float(data["interest_saved"]) >= 0
            assert data["months_saved"] >= 0

    @pytest.mark.asyncio
    async def test_save_plan_after_optimize(self, async_client):
        """Save a repayment plan -> 200 with plan_id."""
        mock_plan = _make_mock_plan()

        with patch("app.api.routes.optimizer.RepaymentPlanRepository") as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.create.return_value = mock_plan

            resp = await async_client.post("/api/optimizer/save-plan", json={
                "name": "My Avalanche Plan",
                "strategy": "avalanche",
                "config": {"monthly_extra": 5000},
                "results": {"interest_saved": 100000},
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "plan_id" in data
            assert data["plan_id"] == str(mock_plan.id)
            assert "message" in data

    @pytest.mark.asyncio
    async def test_list_saved_plans(self, async_client):
        """List saved plans returns 2 plans -> 200."""
        plan_a = _make_mock_plan(name="Plan A", strategy="avalanche")
        plan_b = _make_mock_plan(name="Plan B", strategy="snowball")

        with patch("app.api.routes.optimizer.RepaymentPlanRepository") as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.list_by_user.return_value = [plan_a, plan_b]

            resp = await async_client.get("/api/optimizer/plans")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["name"] == "Plan A"
            assert data[1]["name"] == "Plan B"


# ===========================================================================
# TestUserIsolation
# ===========================================================================

class TestUserIsolation:
    """Tests that users cannot access other users' resources."""

    @pytest.mark.asyncio
    async def test_get_loan_not_owned_returns_404(self, async_client):
        """GET /api/loans/{other_id} when repo returns None -> 404."""
        with patch("app.api.routes.loans.LoanRepository") as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.get_by_id.return_value = None

            resp = await async_client.get(f"/api/loans/{OTHER_LOAN_ID}")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Loan not found"

    @pytest.mark.asyncio
    async def test_delete_loan_not_owned_returns_404(self, async_client):
        """DELETE /api/loans/{other_id} when repo returns False -> 404."""
        with patch("app.api.routes.loans.LoanRepository") as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.delete.return_value = False

            resp = await async_client.delete(f"/api/loans/{OTHER_LOAN_ID}")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Loan not found"

    @pytest.mark.asyncio
    async def test_plans_scoped_to_user(self, async_client):
        """GET /api/optimizer/plans with no plans -> 200 empty list."""
        with patch("app.api.routes.optimizer.RepaymentPlanRepository") as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.list_by_user.return_value = []

            resp = await async_client.get("/api/optimizer/plans")
            assert resp.status_code == 200
            assert resp.json() == []


# ===========================================================================
# TestTaxImpact
# ===========================================================================

class TestTaxImpact:
    """Tests for the tax-impact endpoint across India and US regimes."""

    @pytest.mark.asyncio
    async def test_tax_impact_in_user_with_home_loan(self, async_client):
        """IN user with home loan (80c+24b) -> 200 with old/new regime."""
        home_loan = _make_mock_loan(
            loan_type="home", eligible_80c=True, eligible_24b=True,
        )

        with patch("app.api.routes.optimizer.LoanRepository") as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.list_by_user.return_value = [home_loan]

            resp = await async_client.post("/api/optimizer/tax-impact", json={
                "annual_income": 1200000,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "old_regime_tax" in data
            assert "new_regime_tax" in data
            assert "recommended" in data
            assert "savings" in data
            assert "explanation" in data

    @pytest.mark.asyncio
    async def test_tax_impact_no_loans(self, async_client):
        """IN user with no loans -> 200."""
        with patch("app.api.routes.optimizer.LoanRepository") as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.list_by_user.return_value = []

            resp = await async_client.post("/api/optimizer/tax-impact", json={
                "annual_income": 1200000,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "old_regime_tax" in data
            assert "new_regime_tax" in data

    @pytest.mark.asyncio
    async def test_tax_impact_us_user(self, async_client, mock_user):
        """US user -> 200 with standard/itemized comparison."""
        # Override user to be a US filer
        mock_user.country = "US"
        mock_user.filing_status = "single"

        us_loan = _make_mock_loan(
            loan_type="home",
            eligible_80c=False,
            eligible_24b=False,
            eligible_mortgage_deduction=True,
            eligible_student_loan_deduction=False,
        )

        with patch("app.api.routes.optimizer.LoanRepository") as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.list_by_user.return_value = [us_loan]

            resp = await async_client.post("/api/optimizer/tax-impact", json={
                "annual_income": 80000,
            })
            assert resp.status_code == 200
            data = resp.json()
            # US path returns standard vs itemized via old_regime_tax/new_regime_tax
            assert "old_regime_tax" in data
            assert "new_regime_tax" in data
            assert "recommended" in data

        # Reset for other tests
        mock_user.country = "IN"
        mock_user.filing_status = "individual"


# ===========================================================================
# TestDataExport
# ===========================================================================

class TestDataExport:
    """Tests for POST /api/user/export-data."""

    @pytest.mark.asyncio
    async def test_export_data_structure(self, async_client, mock_loan):
        """Export returns all expected top-level keys."""
        mock_loan.eligible_mortgage_deduction = False
        mock_loan.eligible_student_loan_deduction = False
        mock_plan = _make_mock_plan()
        mock_scan = _make_mock_scan()

        with (
            patch("app.api.routes.user.LoanRepository") as MockLoanRepo,
            patch("app.api.routes.user.RepaymentPlanRepository") as MockPlanRepo,
            patch("app.api.routes.user.ScanJobRepository") as MockScanRepo,
        ):
            MockLoanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[mock_loan]))
            MockPlanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[mock_plan]))
            MockScanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[mock_scan]))

            resp = await async_client.post("/api/user/export-data")
            assert resp.status_code == 200
            data = resp.json()
            assert "exported_at" in data
            assert "profile" in data
            assert "loans" in data
            assert "repayment_plans" in data
            assert "scan_jobs" in data
            assert len(data["loans"]) == 1
            assert len(data["repayment_plans"]) == 1
            assert len(data["scan_jobs"]) == 1

    @pytest.mark.asyncio
    async def test_export_data_empty(self, async_client):
        """Export with no data returns empty arrays."""
        with (
            patch("app.api.routes.user.LoanRepository") as MockLoanRepo,
            patch("app.api.routes.user.RepaymentPlanRepository") as MockPlanRepo,
            patch("app.api.routes.user.ScanJobRepository") as MockScanRepo,
        ):
            MockLoanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))
            MockPlanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))
            MockScanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))

            resp = await async_client.post("/api/user/export-data")
            assert resp.status_code == 200
            data = resp.json()
            assert data["loans"] == []
            assert data["repayment_plans"] == []
            assert data["scan_jobs"] == []

    @pytest.mark.asyncio
    async def test_export_data_content_disposition(self, async_client):
        """Content-Disposition header contains 'loan-data-export-'."""
        with (
            patch("app.api.routes.user.LoanRepository") as MockLoanRepo,
            patch("app.api.routes.user.RepaymentPlanRepository") as MockPlanRepo,
            patch("app.api.routes.user.ScanJobRepository") as MockScanRepo,
        ):
            MockLoanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))
            MockPlanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))
            MockScanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))

            resp = await async_client.post("/api/user/export-data")
            assert resp.status_code == 200
            cd = resp.headers.get("content-disposition", "")
            assert "loan-data-export-" in cd

    @pytest.mark.asyncio
    async def test_export_data_profile_has_country(self, async_client):
        """Profile dict includes country and filing_status."""
        with (
            patch("app.api.routes.user.LoanRepository") as MockLoanRepo,
            patch("app.api.routes.user.RepaymentPlanRepository") as MockPlanRepo,
            patch("app.api.routes.user.ScanJobRepository") as MockScanRepo,
        ):
            MockLoanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))
            MockPlanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))
            MockScanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))

            resp = await async_client.post("/api/user/export-data")
            assert resp.status_code == 200
            profile = resp.json()["profile"]
            assert "country" in profile
            assert profile["country"] == "IN"
            assert "filing_status" in profile
            assert profile["filing_status"] == "individual"

    @pytest.mark.asyncio
    async def test_export_data_loans_serialized(self, async_client):
        """Serialized loan dict has all expected keys."""
        loan = _make_mock_loan()

        with (
            patch("app.api.routes.user.LoanRepository") as MockLoanRepo,
            patch("app.api.routes.user.RepaymentPlanRepository") as MockPlanRepo,
            patch("app.api.routes.user.ScanJobRepository") as MockScanRepo,
        ):
            MockLoanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[loan]))
            MockPlanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))
            MockScanRepo.return_value = AsyncMock(list_by_user=AsyncMock(return_value=[]))

            resp = await async_client.post("/api/user/export-data")
            assert resp.status_code == 200
            loans = resp.json()["loans"]
            assert len(loans) == 1
            loan_dict = loans[0]
            expected_keys = {
                "id", "bank_name", "loan_type", "principal_amount",
                "outstanding_principal", "interest_rate", "interest_rate_type",
                "tenure_months", "remaining_tenure_months", "emi_amount",
                "emi_due_date", "status", "eligible_80c", "eligible_24b",
                "eligible_80e", "eligible_80eea", "eligible_mortgage_deduction",
                "eligible_student_loan_deduction", "created_at",
            }
            assert expected_keys.issubset(set(loan_dict.keys()))


# ===========================================================================
# TestHealthEndpoints
# ===========================================================================

class TestHealthEndpoints:
    """Tests for /api/health, /api/health/ready, /api/health/startup."""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        """GET /api/health -> 200 with status=healthy."""
        resp = await async_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_health_ready_db_ok(self, async_client):
        """Readiness probe with successful DB -> 200."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine = AsyncMock()
        mock_engine.connect = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=False),
        ))

        with patch("app.db.session.engine", mock_engine):
            resp = await async_client.get("/api/health/ready")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ready"
            assert data["database"] is True

    @pytest.mark.asyncio
    async def test_health_ready_db_fail(self, async_client):
        """Readiness probe with DB failure -> 503."""
        mock_engine = AsyncMock()
        mock_engine.connect = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(side_effect=Exception("Connection refused")),
            __aexit__=AsyncMock(return_value=False),
        ))

        with patch("app.db.session.engine", mock_engine):
            resp = await async_client.get("/api/health/ready")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "unavailable"
            assert data["database"] is False

    @pytest.mark.asyncio
    async def test_health_startup_schema_ok(self, async_client):
        """Startup probe with schema present -> 200."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine = AsyncMock()
        mock_engine.connect = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=False),
        ))

        with patch("app.db.session.engine", mock_engine):
            resp = await async_client.get("/api/health/startup")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "started"
            assert data["schema_ready"] is True

    @pytest.mark.asyncio
    async def test_health_startup_schema_fail(self, async_client):
        """Startup probe with missing schema -> 503."""
        mock_engine = AsyncMock()
        mock_engine.connect = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(side_effect=Exception("relation does not exist")),
            __aexit__=AsyncMock(return_value=False),
        ))

        with patch("app.db.session.engine", mock_engine):
            resp = await async_client.get("/api/health/startup")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "starting"
            assert data["schema_ready"] is False

    @pytest.mark.asyncio
    async def test_health_version_field(self, async_client):
        """All health endpoints include version=0.1.0."""
        # /api/health - no DB needed
        resp1 = await async_client.get("/api/health")
        assert resp1.json()["version"] == "0.1.0"

        # /api/health/ready - mock DB success
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine = AsyncMock()
        mock_engine.connect = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=False),
        ))

        with patch("app.db.session.engine", mock_engine):
            resp2 = await async_client.get("/api/health/ready")
            assert resp2.json()["version"] == "0.1.0"

            resp3 = await async_client.get("/api/health/startup")
            assert resp3.json()["version"] == "0.1.0"
