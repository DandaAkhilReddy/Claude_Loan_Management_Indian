"""API usage log repository — tracking and aggregation."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApiUsageLog


class UsageLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        service: str,
        operation: str,
        user_id: uuid.UUID | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        estimated_cost: float = 0,
        metadata: dict | None = None,
    ) -> ApiUsageLog:
        entry = ApiUsageLog(
            user_id=user_id,
            service=service,
            operation=operation,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            estimated_cost=estimated_cost,
            metadata_json=metadata,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_summary(self, days: int = 30) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(
                ApiUsageLog.service,
                func.count(ApiUsageLog.id).label("call_count"),
                func.sum(ApiUsageLog.estimated_cost).label("total_cost"),
                func.sum(ApiUsageLog.tokens_input).label("total_tokens_in"),
                func.sum(ApiUsageLog.tokens_output).label("total_tokens_out"),
            )
            .where(ApiUsageLog.created_at >= cutoff)
            .group_by(ApiUsageLog.service)
        )
        rows = result.all()

        by_service = {}
        total_calls = 0
        total_cost = Decimal("0")
        for row in rows:
            cost = row.total_cost or Decimal("0")
            by_service[row.service] = {
                "call_count": row.call_count,
                "total_cost": float(cost),
                "tokens_input": row.total_tokens_in or 0,
                "tokens_output": row.total_tokens_out or 0,
            }
            total_calls += row.call_count
            total_cost += cost

        return {
            "total_calls": total_calls,
            "total_cost": float(total_cost),
            "by_service": by_service,
        }

    async def get_daily_breakdown(self, days: int = 30) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(
                cast(ApiUsageLog.created_at, Date).label("date"),
                ApiUsageLog.service,
                func.count(ApiUsageLog.id).label("call_count"),
                func.sum(ApiUsageLog.estimated_cost).label("total_cost"),
            )
            .where(ApiUsageLog.created_at >= cutoff)
            .group_by("date", ApiUsageLog.service)
            .order_by("date")
        )
        rows = result.all()
        return [
            {
                "date": str(row.date),
                "service": row.service,
                "call_count": row.call_count,
                "total_cost": float(row.total_cost or 0),
            }
            for row in rows
        ]
