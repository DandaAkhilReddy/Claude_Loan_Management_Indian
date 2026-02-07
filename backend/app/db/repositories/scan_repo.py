"""Scan job repository."""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ScanJob


class ScanJobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: uuid.UUID, blob_url: str, original_filename: str, file_size_bytes: int, mime_type: str) -> ScanJob:
        job = ScanJob(
            user_id=user_id,
            blob_url=blob_url,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_by_id(self, job_id: uuid.UUID, user_id: uuid.UUID) -> ScanJob | None:
        result = await self.session.execute(
            select(ScanJob).where(ScanJob.id == job_id, ScanJob.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, job_id: uuid.UUID, status: str, **kwargs) -> ScanJob | None:
        result = await self.session.execute(select(ScanJob).where(ScanJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return None
        job.status = status
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        await self.session.flush()
        return job

    async def list_by_user(self, user_id: uuid.UUID) -> list[ScanJob]:
        result = await self.session.execute(
            select(ScanJob).where(ScanJob.user_id == user_id).order_by(ScanJob.created_at.desc())
        )
        return list(result.scalars().all())
