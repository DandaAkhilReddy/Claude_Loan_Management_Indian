"""Loan repository — CRUD with user scoping and filtering."""

import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Loan


class LoanRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, loan_id: uuid.UUID, user_id: uuid.UUID) -> Loan | None:
        result = await self.session.execute(
            select(Loan).where(and_(Loan.id == loan_id, Loan.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        loan_type: str | None = None,
        status: str | None = None,
        bank_name: str | None = None,
    ) -> list[Loan]:
        query = select(Loan).where(Loan.user_id == user_id)
        if loan_type:
            query = query.where(Loan.loan_type == loan_type)
        if status:
            query = query.where(Loan.status == status)
        if bank_name:
            query = query.where(Loan.bank_name == bank_name)
        query = query.order_by(Loan.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, user_id: uuid.UUID, **kwargs) -> Loan:
        loan = Loan(user_id=user_id, **kwargs)
        self.session.add(loan)
        await self.session.flush()
        return loan

    async def update(self, loan_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Loan | None:
        loan = await self.get_by_id(loan_id, user_id)
        if not loan:
            return None
        for key, value in kwargs.items():
            if hasattr(loan, key) and key not in ("id", "user_id", "created_at"):
                setattr(loan, key, value)
        await self.session.flush()
        return loan

    async def delete(self, loan_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        loan = await self.get_by_id(loan_id, user_id)
        if not loan:
            return False
        await self.session.delete(loan)
        await self.session.flush()
        return True
