"""Semantic search service for finding relevant ads and user video segments using embeddings."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad import Ad
from app.models.user_video_segment import UserVideoSegment
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

    async def search_project_segments(
        self,
        db: AsyncSession,
        project_id: UUID,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> list[tuple[UserVideoSegment, float]]:
        """
        Search user video segments within a specific project using semantic similarity.

        This is the core retrieval method for the ad generation pipeline:
        1. Writer Agent generates search queries for each slot in the visual script
        2. This method finds the best matching user clips for each query
        3. Director Agent then selects final clips based on these results

        Args:
            db: Database session
            project_id: UUID of the project to search within
            query: Search query (e.g., "energetic action, product reveal, surprised reaction")
            limit: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0), defaults to 0.5

        Returns:
            list[tuple[UserVideoSegment, float]]: List of (segment, similarity_score) tuples,
            ordered by descending similarity
        """
        # Generate embedding for search query
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Search using pgvector cosine distance, scoped to project
        # Only select id and similarity - we'll batch fetch full objects after
        search_query = text(
            """
            SELECT
                id,
                (1 - (embedding <=> CAST(:query_embedding AS vector))) as similarity
            FROM user_video_segments
            WHERE project_id = :project_id
                AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
            """
        )

        result = await db.execute(
            search_query,
            {
                "query_embedding": query_embedding,
                "project_id": project_id,
                "limit": limit,
            },
        )

        rows = result.fetchall()

        # Filter by min_similarity and collect IDs
        id_to_similarity = {}
        for row in rows:
            similarity = row.similarity
            if similarity >= min_similarity:
                id_to_similarity[row.id] = similarity

        if not id_to_similarity:
            logger.info(
                f"Project segment search for '{query[:50]}...' in project {project_id} "
                f"found 0 results"
            )
            return []

        # Batch fetch all matching segments in a single query
        segment_result = await db.execute(
            select(UserVideoSegment).where(UserVideoSegment.id.in_(id_to_similarity.keys()))
        )
        segments_by_id = {s.id: s for s in segment_result.scalars().all()}

        # Build results maintaining similarity order
        results = []
        for segment_id, similarity in id_to_similarity.items():
            if segment_id in segments_by_id:
                results.append((segments_by_id[segment_id], similarity))

        logger.info(
            f"Project segment search for '{query[:50]}...' in project {project_id} "
            f"found {len(results)} results"
        )

        return results

    async def search_project_segments_batch(
        self,
        db: AsyncSession,
        project_id: UUID,
        queries: list[str],
        limit_per_query: int = 5,
        min_similarity: float = 0.5,
    ) -> dict[str, list[tuple[UserVideoSegment, float]]]:
        """
        Batch search for multiple queries within a project.

        Useful for searching for clips for all slots in a visual script at once.

        Args:
            db: Database session
            project_id: UUID of the project to search within
            queries: List of search queries (one per slot)
            limit_per_query: Maximum results per query
            min_similarity: Minimum similarity threshold

        Returns:
            dict mapping query string to list of (segment, similarity) tuples
        """
        results = {}

        for query in queries:
            query_results = await self.search_project_segments(
                db=db,
                project_id=project_id,
                query=query,
                limit=limit_per_query,
                min_similarity=min_similarity,
            )
            results[query] = query_results

        logger.info(f"Batch search completed: {len(queries)} queries in project {project_id}")

        return results

    async def search_slots_in_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        slots: list[dict[str, Any]],
        limit_per_slot: int = 5,
        min_similarity: float = 0.5,
    ) -> dict[str, list[tuple[UserVideoSegment, float]]]:
        """
        Search for clips matching visual script slots within a project.

        This method is designed to work directly with the output of ContentPlanningAgent:
        - Takes slots with search_query field
        - Returns results keyed by slot_id

        Args:
            db: Database session
            project_id: UUID of the project to search within
            slots: List of slot dicts with at least 'id' and 'search_query' fields
            limit_per_slot: Maximum results per slot
            min_similarity: Minimum similarity threshold

        Returns:
            dict mapping slot_id to list of (segment, similarity) tuples

        Example:
            slots = [
                {"id": "slot_01_hook", "search_query": "energetic action, surprise"},
                {"id": "slot_02_problem", "search_query": "frustrated expression, leak"}
            ]
            results = await service.search_slots_in_project(db, project_id, slots)
            # results = {
            #     "slot_01_hook": [(segment1, 0.89), (segment2, 0.76)],
            #     "slot_02_problem": [(segment3, 0.82), (segment4, 0.71)]
            # }
        """
        results = {}

        for slot in slots:
            slot_id = slot.get("id")
            search_query = slot.get("search_query")

            if not slot_id or not search_query:
                logger.warning(f"Skipping slot without id or search_query: {slot}")
                continue

            slot_results = await self.search_project_segments(
                db=db,
                project_id=project_id,
                query=search_query,
                limit=limit_per_slot,
                min_similarity=min_similarity,
            )
            results[slot_id] = slot_results

        logger.info(f"Slot search completed: {len(results)} slots searched in project {project_id}")

        return results

    async def find_similar_segments_in_project(
        self,
        db: AsyncSession,
        segment_id: UUID,
        project_id: UUID,
        limit: int = 5,
        min_similarity: float = 0.6,
    ) -> list[tuple[UserVideoSegment, float]]:
        """
        Find segments similar to a specific segment within the same project.

        Useful for "find similar clips" functionality in the editor.

        Args:
            db: Database session
            segment_id: ID of segment to find similar segments for
            project_id: UUID of the project to search within
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold

        Returns:
            list[tuple[UserVideoSegment, float]]: List of (segment, similarity_score) tuples
        """
        # Get the source segment
        result = await db.execute(select(UserVideoSegment).where(UserVideoSegment.id == segment_id))
        source_segment = result.scalar_one_or_none()

        if not source_segment:
            logger.warning(f"Segment {segment_id} not found")
            return []

        if not source_segment.embedding:
            logger.warning(f"Segment {segment_id} has no embedding")
            return []

        if source_segment.project_id != project_id:
            logger.warning(
                f"Segment {segment_id} belongs to project {source_segment.project_id}, "
                f"not {project_id}"
            )
            return []

        # Search using the source segment's embedding
        search_query = text(
            """
            SELECT
                id,
                (1 - (embedding <=> CAST(:source_embedding AS vector))) as similarity
            FROM user_video_segments
            WHERE project_id = :project_id
                AND id != :segment_id
                AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:source_embedding AS vector)
            LIMIT :limit
            """
        )

        result = await db.execute(
            search_query,
            {
                "source_embedding": source_segment.embedding,
                "project_id": project_id,
                "segment_id": segment_id,
                "limit": limit,
            },
        )

        rows = result.fetchall()

        # Filter by min_similarity and collect IDs
        id_to_similarity = {}
        for row in rows:
            if row.similarity >= min_similarity:
                id_to_similarity[row.id] = row.similarity

        if not id_to_similarity:
            logger.info(f"Found 0 segments similar to segment {segment_id} in project {project_id}")
            return []

        # Batch fetch all matching segments in a single query
        segment_result = await db.execute(
            select(UserVideoSegment).where(UserVideoSegment.id.in_(id_to_similarity.keys()))
        )
        segments_by_id = {s.id: s for s in segment_result.scalars().all()}

        # Build results maintaining similarity order
        results = []
        for seg_id, similarity in id_to_similarity.items():
            if seg_id in segments_by_id:
                results.append((segments_by_id[seg_id], similarity))

        logger.info(
            f"Found {len(results)} segments similar to segment {segment_id} "
            f"in project {project_id}"
        )

        return results
