"""Embedding repository — pgvector cosine similarity search."""

import uuid
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentEmbedding


class EmbeddingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, source_type: str, source_id: str, chunk_text: str, embedding: list[float], metadata: dict | None = None) -> DocumentEmbedding:
        # Check if exists
        result = await self.session.execute(
            select(DocumentEmbedding).where(
                DocumentEmbedding.source_type == source_type,
                DocumentEmbedding.source_id == source_id,
                DocumentEmbedding.chunk_text == chunk_text,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.embedding = embedding
            existing.metadata_json = metadata
        else:
            existing = DocumentEmbedding(
                source_type=source_type,
                source_id=source_id,
                chunk_text=chunk_text,
                embedding=embedding,
                metadata_json=metadata,
            )
            self.session.add(existing)

        await self.session.flush()
        return existing

    async def similarity_search(
        self,
        query_embedding: list[float],
        source_type: str | None = None,
        limit: int = 5,
    ) -> list[DocumentEmbedding]:
        """Find most similar embeddings using cosine distance."""
        query = (
            select(DocumentEmbedding)
            .order_by(DocumentEmbedding.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        if source_type:
            query = query.where(DocumentEmbedding.source_type == source_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())
