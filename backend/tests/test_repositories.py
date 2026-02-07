"""Tests for database repositories (mocked AsyncSession)."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.db.repositories.loan_repo import LoanRepository
from app.db.repositories.user_repo import UserRepository
from app.db.repositories.scan_repo import ScanJobRepository
from app.db.repositories.plan_repo import RepaymentPlanRepository

MOCK_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
MOCK_LOAN_ID = uuid.UUID("00000000-0000-4000-a000-000000000010")


# ---------------------------------------------------------------------------
# LoanRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestLoanRepository:
    @pytest.fixture
    def repo(self, mock_db_session):
        return LoanRepository(mock_db_session)

    async def test_create_loan(self, repo, mock_db_session):
        mock_db_session.add = MagicMock()
        mock_db_session.flush = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        result = await repo.create(
            MOCK_USER_ID,
            bank_name="SBI",
            loan_type="home",
            principal_amount=5000000,
            outstanding_principal=4500000,
            interest_rate=8.5,
            interest_rate_type="floating",
            tenure_months=240,
            remaining_tenure_months=220,
            emi_amount=43391,
        )
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

    async def test_get_by_id(self, repo, mock_db_session):
        from app.db.models import Loan

        mock_loan = MagicMock(spec=Loan)
        mock_loan.id = MOCK_LOAN_ID
        mock_loan.user_id = MOCK_USER_ID

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_loan
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(MOCK_LOAN_ID, MOCK_USER_ID)
        assert result is not None
        assert result.id == MOCK_LOAN_ID

    async def test_get_by_id_not_found(self, repo, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(MOCK_LOAN_ID, MOCK_USER_ID)
        assert result is None

    async def test_list_by_user(self, repo, mock_db_session):
        from app.db.models import Loan

        mock_loan = MagicMock(spec=Loan)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_loan]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_user(MOCK_USER_ID)
        assert len(result) == 1

    async def test_delete(self, repo, mock_db_session):
        from app.db.models import Loan

        mock_loan = MagicMock(spec=Loan)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_loan
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.delete = AsyncMock()
        mock_db_session.flush = AsyncMock()

        result = await repo.delete(MOCK_LOAN_ID, MOCK_USER_ID)
        assert result is True
        mock_db_session.delete.assert_called_once()


# ---------------------------------------------------------------------------
# UserRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestUserRepository:
    @pytest.fixture
    def repo(self, mock_db_session):
        return UserRepository(mock_db_session)

    async def test_get_by_firebase_uid(self, repo, mock_db_session):
        from app.db.models import User

        mock_user = MagicMock(spec=User)
        mock_user.firebase_uid = "test_uid"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_firebase_uid("test_uid")
        assert result is not None
        assert result.firebase_uid == "test_uid"

    async def test_get_by_firebase_uid_not_found(self, repo, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_firebase_uid("nonexistent")
        assert result is None

    async def test_upsert_creates_new(self, repo, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.add = MagicMock()
        mock_db_session.flush = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        result = await repo.upsert(
            firebase_uid="new_uid",
            email="new@example.com",
            phone=None,
            display_name="New User",
        )
        mock_db_session.add.assert_called_once()


# ---------------------------------------------------------------------------
# ScanRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestScanJobRepository:
    @pytest.fixture
    def repo(self, mock_db_session):
        return ScanJobRepository(mock_db_session)

    async def test_create(self, repo, mock_db_session):
        mock_db_session.add = MagicMock()
        mock_db_session.flush = AsyncMock()

        result = await repo.create(
            MOCK_USER_ID, "documents/test.pdf", "test.pdf",
            file_size_bytes=1024, mime_type="application/pdf",
        )
        mock_db_session.add.assert_called_once()

    async def test_get_by_id(self, repo, mock_db_session):
        from app.db.models import ScanJob

        mock_scan = MagicMock(spec=ScanJob)
        mock_scan.id = uuid.uuid4()
        mock_scan.user_id = MOCK_USER_ID

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_scan
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(mock_scan.id, MOCK_USER_ID)
        assert result is not None


# ---------------------------------------------------------------------------
# PlanRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRepaymentPlanRepository:
    @pytest.fixture
    def repo(self, mock_db_session):
        return RepaymentPlanRepository(mock_db_session)

    async def test_create(self, repo, mock_db_session):
        mock_db_session.add = MagicMock()
        mock_db_session.flush = AsyncMock()

        result = await repo.create(
            user_id=MOCK_USER_ID,
            name="Test Plan",
            strategy="avalanche",
            config={"monthly_extra": 10000},
            results={"interest_saved": 250000},
        )
        mock_db_session.add.assert_called_once()

    async def test_list_by_user(self, repo, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_user(MOCK_USER_ID)
        assert result == []
