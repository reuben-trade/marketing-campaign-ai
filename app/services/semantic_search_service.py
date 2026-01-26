"""Semantic search service for finding relevant ads using embeddings."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad import Ad
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SemanticSearchService:
    """
    Semantic search and relevance filtering for ads using pgvector.
    """

    def __init__(self) -> None:
        """Initialize the semantic search service."""
        self.embedding_service = EmbeddingService()

    async def search_ads(
        self,
        db: AsyncSession,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[tuple[Ad, float]]:
        """
        Semantic search across ads using pgvector.

        Process:
        1. Generate embedding for query
        2. Use pgvector cosine distance operator: embedding <=> query_embedding
        3. Apply additional filters (creative_type, date_range, etc.)
        4. Order by similarity (ascending distance = descending similarity)
        5. HNSW index automatically used for fast search

        Args:
            db: Database session
            query: Search query text
            filters: Additional filters (creative_type, analyzed, etc.)
            limit: Maximum number of results

        Returns:
            list[tuple[Ad, float]]: List of (ad, similarity_score) tuples
        """
        # Generate embedding for search query
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Use EmbeddingService's find_similar_ads method
        results = await self.embedding_service.find_similar_ads(
            db=db,
            query_embedding=query_embedding,
            limit=limit,
            filters=filters,
        )

        logger.info(f"Semantic search for '{query[:50]}...' found {len(results)} results")

        return results

    async def filter_relevant_ads(
        self,
        db: AsyncSession,
        intent_description: str,
        intent_themes: list[str],
        min_similarity: float = 0.7,
    ) -> list[Ad]:
        """
        Filter ads by relevance to user's advertising intent using pgvector.
        Used in recommendations/feedback to exclude irrelevant ads.

        Args:
            db: Database session
            intent_description: Description of what user wants to advertise
            intent_themes: List of specific themes/ideas to focus on
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            list[Ad]: List of relevant ads
        """
        # Combine description and themes into a search query
        query_parts = [intent_description]
        if intent_themes:
            query_parts.append("Themes: " + ", ".join(intent_themes))

        query = " | ".join(query_parts)

        # Generate embedding for the intent
        intent_embedding = await self.embedding_service.generate_embedding(query)

        # Find similar ads (no limit to get all relevant ads)
        results = await self.embedding_service.find_similar_ads(
            db=db,
            query_embedding=intent_embedding,
            limit=1000,  # Large limit to get all relevant ads
            min_similarity=min_similarity,
            filters={"analyzed": True, "analysis_status": "completed"},
        )

        # Extract just the ads (without similarity scores)
        relevant_ads = [ad for ad, _ in results]

        logger.info(
            f"Filtered to {len(relevant_ads)} relevant ads "
            f"for intent: {intent_description[:50]}..."
        )

        return relevant_ads

    async def calculate_relevance_matrix(
        self,
        db: AsyncSession,
        target_ad: Ad,
        candidate_ads: list[Ad],
    ) -> dict[UUID, float]:
        """
        Calculate similarity scores between target ad and candidates using pgvector.

        Args:
            db: Database session
            target_ad: Ad to compare against
            candidate_ads: List of ads to compare with target

        Returns:
            dict[UUID, float]: Dict of {ad_id: similarity_score}
        """
        if not target_ad.embedding:
            logger.warning(f"Target ad {target_ad.id} has no embedding")
            return {}

        if not candidate_ads:
            return {}

        # Get IDs of candidate ads
        candidate_ids = [ad.id for ad in candidate_ads]

        # Use batch query with ANY clause for efficiency
        # SELECT id, (1 - (embedding <=> target_embedding)) as similarity
        # FROM ads
        # WHERE id = ANY(%s)
        query = text(
            """
            SELECT
                id,
                (1 - (embedding <=> CAST(:target_embedding AS vector))) as similarity
            FROM ads
            WHERE id = ANY(:candidate_ids)
                AND embedding IS NOT NULL
        """
        )

        result = await db.execute(
            query,
            {
                "target_embedding": target_ad.embedding,
                "candidate_ids": candidate_ids,
            },
        )

        rows = result.fetchall()

        # Build relevance matrix
        relevance_matrix = {}
        for row in rows:
            ad_id = row.id
            similarity = row.similarity
            relevance_matrix[ad_id] = similarity

        logger.info(
            f"Calculated relevance matrix for {len(relevance_matrix)} ads "
            f"against target ad {target_ad.id}"
        )

        return relevance_matrix

    async def find_similar_to_ad(
        self,
        db: AsyncSession,
        ad_id: UUID,
        limit: int = 10,
        min_similarity: float = 0.7,
    ) -> list[tuple[Ad, float]]:
        """
        Find ads similar to a specific ad.

        Args:
            db: Database session
            ad_id: ID of ad to find similar ads for
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            list[tuple[Ad, float]]: List of (ad, similarity_score) tuples
        """
        # Get the target ad
        result = await db.execute(select(Ad).where(Ad.id == ad_id))
        target_ad = result.scalar_one_or_none()

        if not target_ad:
            logger.warning(f"Ad {ad_id} not found")
            return []

        if not target_ad.embedding:
            logger.warning(f"Ad {ad_id} has no embedding")
            return []

        # Find similar ads using the embedding
        results = await self.embedding_service.find_similar_ads(
            db=db,
            query_embedding=target_ad.embedding,
            limit=limit + 1,  # +1 to exclude self
            min_similarity=min_similarity,
        )

        # Exclude the target ad itself from results
        results = [(ad, sim) for ad, sim in results if ad.id != ad_id][:limit]

        logger.info(f"Found {len(results)} ads similar to ad {ad_id}")

        return results
