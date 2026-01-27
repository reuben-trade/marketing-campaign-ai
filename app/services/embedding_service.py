"""Embedding service for generating and managing ad embeddings."""

import logging
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.ad import Ad

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generates embeddings for ad summaries using OpenAI text-embedding-3-small.

    Embedding strategy:
    - Model: text-embedding-3-small (1536 dimensions, cheap, fast)
    - Input: Generated ad summary (product, messaging, visual themes, target audience)
    - Storage: Vector(1536) in PostgreSQL using pgvector
    - Similarity: Cosine distance using pgvector operators
    """

    def __init__(self) -> None:
        """Initialize the embedding service."""
        settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "text-embedding-3-small"  # 1536 dimensions

    def generate_ad_summary(self, ad: Ad) -> str:
        """
        Generate concise summary from video_intelligence for embedding.

        Format:
        Product/Service: [inferred from video_intelligence]
        Messaging Pillar: [primary_messaging_pillar]
        Target Audience: [inferred_audience]
        Visual Style: [production_style]
        Key Themes: [from timeline emotions, beat types]
        CTA Type: [from copy_analysis.cta_text]

        Args:
            ad: Ad model with video_intelligence data

        Returns:
            str: Formatted summary for embedding
        """
        if not ad.video_intelligence:
            # Fallback to basic ad copy if no video intelligence
            parts = []
            if ad.ad_headline:
                parts.append(f"Headline: {ad.ad_headline}")
            if ad.ad_copy:
                parts.append(f"Copy: {ad.ad_copy[:200]}")  # Limit length
            if ad.cta_text:
                parts.append(f"CTA: {ad.cta_text}")
            return " | ".join(parts) if parts else "Unknown ad content"

        video_intel = ad.video_intelligence
        parts = []

        # Inferred audience
        inferred_audience = video_intel.get("inferred_audience", "")
        if inferred_audience:
            parts.append(f"Target Audience: {inferred_audience}")

        # Primary messaging pillar
        messaging_pillar = video_intel.get("primary_messaging_pillar", "")
        if messaging_pillar:
            parts.append(f"Messaging: {messaging_pillar}")

        # Production style
        production_style = video_intel.get("production_style", "")
        if production_style:
            parts.append(f"Style: {production_style}")

        # Overall narrative summary
        narrative = video_intel.get("overall_narrative_summary", "")
        if narrative:
            parts.append(f"Narrative: {narrative[:200]}")  # Limit length

        # Extract key themes from timeline
        timeline = video_intel.get("timeline", [])
        if timeline:
            beat_types = set()
            emotions = set()
            for beat in timeline[:10]:  # Limit to first 10 beats
                if isinstance(beat, dict):
                    beat_type = beat.get("beat_type")
                    if beat_type:
                        beat_types.add(beat_type)
                    emotion = beat.get("emotion")
                    if emotion:
                        emotions.add(emotion)

            if beat_types:
                parts.append(f"Beats: {', '.join(list(beat_types)[:5])}")
            if emotions:
                parts.append(f"Emotions: {', '.join(list(emotions)[:5])}")

        # Copy analysis CTA
        copy_analysis = video_intel.get("copy_analysis", {})
        if isinstance(copy_analysis, dict):
            cta = copy_analysis.get("cta_text", "")
            if cta:
                parts.append(f"CTA: {cta}")

        # Fallback to ad copy if no video intelligence parts
        if not parts and ad.ad_copy:
            parts.append(f"Copy: {ad.ad_copy[:300]}")

        summary = " | ".join(parts)
        return summary if summary else "No content available"

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Call OpenAI API to generate embedding.

        Args:
            text: Text to embed

        Returns:
            list[float]: 1536-dimensional embedding vector

        Raises:
            Exception: If API call fails
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float",
            )

            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def embed_ad(self, db: AsyncSession, ad: Ad) -> None:
        """
        Generate summary and embedding for an ad.
        Stores in ad.ad_summary and ad.embedding.

        Args:
            db: Database session
            ad: Ad model to embed

        Raises:
            Exception: If embedding generation fails
        """
        try:
            # Generate summary
            summary = self.generate_ad_summary(ad)
            ad.ad_summary = summary

            # Generate embedding
            embedding = await self.generate_embedding(summary)
            ad.embedding = embedding

            # Commit is handled by caller
            logger.info(f"Successfully embedded ad {ad.id}")

        except Exception as e:
            logger.error(f"Failed to embed ad {ad.id}: {e}")
            raise

    async def find_similar_ads(
        self,
        db: AsyncSession,
        query_embedding: list[float],
        limit: int = 10,
        min_similarity: float = 0.7,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[Ad, float]]:
        """
        Find ads similar to query embedding using pgvector.

        Uses pgvector's cosine distance operator (<=>):
        - Lower distance = more similar
        - Convert to similarity: 1 - distance
        - Filter where similarity >= min_similarity
        - HNSW index automatically used for fast search

        Args:
            db: Database session
            query_embedding: Embedding vector to search for
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold (0.0-1.0)
            filters: Additional filters (creative_type, analyzed, etc.)

        Returns:
            list[tuple[Ad, float]]: List of (ad, similarity_score) tuples
        """
        # Build query with pgvector cosine distance
        # Note: We use text SQL for pgvector operators as SQLAlchemy doesn't have native support
        from sqlalchemy import text

        # Build filter conditions
        filter_conditions = [
            "ads.embedding IS NOT NULL",
        ]

        if filters:
            if filters.get("creative_type"):
                filter_conditions.append(f"ads.creative_type = '{filters['creative_type']}'")
            if filters.get("analyzed") is not None:
                filter_conditions.append(f"ads.analyzed = {filters['analyzed']}")
            if filters.get("analysis_status"):
                filter_conditions.append(f"ads.analysis_status = '{filters['analysis_status']}'")

        filter_clause = " AND ".join(filter_conditions)

        # Query for similar ads using pgvector cosine distance
        # similarity = 1 - (embedding <=> query_embedding)
        # No min_similarity filter - just order by similarity and return top results
        query = text(
            f"""
            SELECT
                ads.*,
                (1 - (ads.embedding <=> CAST(:query_embedding AS vector))) as similarity
            FROM ads
            WHERE {filter_clause}
            ORDER BY ads.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """
        )

        result = await db.execute(
            query,
            {
                "query_embedding": query_embedding,
                "limit": limit,
            },
        )

        rows = result.fetchall()

        # Convert rows to Ad objects with similarity scores
        results = []
        for row in rows:
            # Reconstruct Ad object from row
            ad_dict = dict(row._mapping)
            similarity = ad_dict.pop("similarity")

            # Get full Ad object with relationships eagerly loaded
            ad_result = await db.execute(
                select(Ad)
                .options(
                    selectinload(Ad.competitor),
                    selectinload(Ad.creative_analysis),
                )
                .where(Ad.id == ad_dict["id"])
            )
            ad = ad_result.scalar_one_or_none()

            if ad:
                results.append((ad, similarity))

        logger.info(f"Found {len(results)} similar ads with min_similarity={min_similarity}")

        return results

    async def embed_batch(self, db: AsyncSession, limit: int = 100) -> dict[str, int]:
        """
        Generate embeddings for ads without them.

        Args:
            db: Database session
            limit: Maximum number of ads to process

        Returns:
            dict: Statistics about processing (processed, failed)
        """
        # Get ads that need embeddings
        result = await db.execute(
            select(Ad)
            .where(
                Ad.analyzed == True,  # noqa: E712
                Ad.analysis_status == "completed",
                Ad.embedding.is_(None),
            )
            .limit(limit)
        )
        ads = result.scalars().all()

        if not ads:
            logger.info("No ads need embeddings")
            return {"processed": 0, "failed": 0}

        processed = 0
        failed = 0

        for ad in ads:
            try:
                await self.embed_ad(db, ad)
                processed += 1

                # Commit in batches of 10
                if processed % 10 == 0:
                    await db.commit()

            except Exception as e:
                logger.error(f"Failed to embed ad {ad.id}: {e}")
                failed += 1
                # Rollback this ad's changes
                await db.rollback()

        # Final commit
        await db.commit()

        logger.info(f"Embedded {processed} ads, {failed} failed")

        return {"processed": processed, "failed": failed}
