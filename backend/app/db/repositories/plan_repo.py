"""Repayment plan repository."""

import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RepaymentPlan


class RepaymentPlanRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: uuid.UUID, name: str, strategy: str, config: dict, results: dict) -> RepaymentPlan:
        plan = RepaymentPlan(
            user_id=user_id,
            name=name,
            strategy=strategy,
            config=config,
            results=results,
        )
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def get_by_id(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> RepaymentPlan | None:
        result = await self.session.execute(
            select(RepaymentPlan).where(
                and_(RepaymentPlan.id == plan_id, RepaymentPlan.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[RepaymentPlan]:
        result = await self.session.execute(
            select(RepaymentPlan).where(RepaymentPlan.user_id == user_id).order_by(RepaymentPlan.created_at.desc())
        )
        return list(result.scalars().all())

    async def set_active(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> RepaymentPlan | None:
        # Deactivate all plans for this user
        plans = await self.list_by_user(user_id)
        for plan in plans:
            plan.is_active = False

        # Activate the selected plan
        target = await self.get_by_id(plan_id, user_id)
        if target:
            target.is_active = True
            await self.session.flush()
        return target
