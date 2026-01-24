"""Search API endpoints for semantic search and relevance."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.schemas.search import (
    AdWithSimilarity,
    EmbedAdsRequest,
    EmbedAdsResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from app.services.embedding_service import EmbeddingService
from app.services.semantic_search_service import SemanticSearchService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/semantic-search", response_model=SemanticSearchResponse)
async def semantic_search(
    db: DbSession,
    request: SemanticSearchRequest,
) -> SemanticSearchResponse:
    """
    Semantic search across ads using embeddings.

    Process:
    1. Generate embedding for search query
    2. Find ads with similar embeddings using pgvector
    3. Apply additional filters if provided
    4. Return ranked results by similarity

    Args:
        request: Search parameters (query, filters, limit, min_similarity)

    Returns:
        SemanticSearchResponse with matching ads and similarity scores
    """
    try:
        search_service = SemanticSearchService()

        # Perform semantic search (ordered by similarity, no threshold filter)
        results = await search_service.search_ads(
            db=db,
            query=request.query,
            filters=request.filters,
            limit=request.limit,
        )

        # Convert to AdWithSimilarity objects
        items = []
        for ad, similarity in results:
            ad_dict = {
                # Basic fields
                "id": ad.id,
                "competitor_id": ad.competitor_id,
                "ad_library_id": ad.ad_library_id,
                "ad_snapshot_url": ad.ad_snapshot_url,
                "creative_type": ad.creative_type,
                "creative_storage_path": ad.creative_storage_path,
                "creative_url": ad.creative_url,
                "ad_copy": ad.ad_copy,
                "ad_headline": ad.ad_headline,
                "ad_description": ad.ad_description,
                "cta_text": ad.cta_text,
                "likes": ad.likes,
                "comments": ad.comments,
                "shares": ad.shares,
                "impressions": ad.impressions,
                "publication_date": ad.publication_date,
                # Detailed fields
                "started_running_date": ad.started_running_date,
                "total_active_time": ad.total_active_time,
                "platforms": ad.platforms,
                "link_headline": ad.link_headline,
                "link_description": ad.link_description,
                "additional_links": ad.additional_links,
                "form_fields": ad.form_fields,
                # Analysis
                "analysis": ad.analysis,
                "video_intelligence": ad.video_intelligence,
                "retrieved_date": ad.retrieved_date,
                "analyzed_date": ad.analyzed_date,
                "analyzed": ad.analyzed,
                "download_status": ad.download_status,
                "analysis_status": ad.analysis_status,
                "total_engagement": ad.total_engagement,
                "overall_score": ad.overall_score,
                # Composite scoring
                "composite_score": ad.composite_score,
                "engagement_rate_percentile": ad.engagement_rate_percentile,
                "survivorship_score": ad.survivorship_score,
                "ad_summary": ad.ad_summary,
                # Duplicate tracking
                "original_ad_id": ad.original_ad_id,
                "duplicate_count": ad.duplicate_count,
                # Similarity score
                "similarity_score": similarity,
            }
            items.append(AdWithSimilarity(**ad_dict))

        return SemanticSearchResponse(
            items=items,
            total=len(items),
            query=request.query,
        )

    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}",
        )


@router.post("/similar-ads/{ad_id}", response_model=list[AdWithSimilarity])
async def find_similar_ads(
    db: DbSession,
    ad_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    min_similarity: float = Query(0.7, ge=0.0, le=1.0),
) -> list[AdWithSimilarity]:
    """
    Find ads similar to a specific ad.

    Args:
        ad_id: ID of ad to find similar ads for
        limit: Maximum number of results
        min_similarity: Minimum similarity threshold (0.0-1.0)

    Returns:
        List of similar ads with similarity scores
    """
    try:
        search_service = SemanticSearchService()

        results = await search_service.find_similar_to_ad(
            db=db,
            ad_id=ad_id,
            limit=limit,
            min_similarity=min_similarity,
        )

        # Convert to AdWithSimilarity objects
        items = []
        for ad, similarity in results:
            ad_dict = {
                # Basic fields
                "id": ad.id,
                "competitor_id": ad.competitor_id,
                "ad_library_id": ad.ad_library_id,
                "ad_snapshot_url": ad.ad_snapshot_url,
                "creative_type": ad.creative_type,
                "creative_storage_path": ad.creative_storage_path,
                "creative_url": ad.creative_url,
                "ad_copy": ad.ad_copy,
                "ad_headline": ad.ad_headline,
                "ad_description": ad.ad_description,
                "cta_text": ad.cta_text,
                "likes": ad.likes,
                "comments": ad.comments,
                "shares": ad.shares,
                "impressions": ad.impressions,
                "publication_date": ad.publication_date,
                # Detailed fields
                "started_running_date": ad.started_running_date,
                "total_active_time": ad.total_active_time,
                "platforms": ad.platforms,
                "link_headline": ad.link_headline,
                "link_description": ad.link_description,
                "additional_links": ad.additional_links,
                "form_fields": ad.form_fields,
                # Analysis
                "analysis": ad.analysis,
                "video_intelligence": ad.video_intelligence,
                "retrieved_date": ad.retrieved_date,
                "analyzed_date": ad.analyzed_date,
                "analyzed": ad.analyzed,
                "download_status": ad.download_status,
                "analysis_status": ad.analysis_status,
                "total_engagement": ad.total_engagement,
                "overall_score": ad.overall_score,
                # Composite scoring
                "composite_score": ad.composite_score,
                "engagement_rate_percentile": ad.engagement_rate_percentile,
                "survivorship_score": ad.survivorship_score,
                "ad_summary": ad.ad_summary,
                # Duplicate tracking
                "original_ad_id": ad.original_ad_id,
                "duplicate_count": ad.duplicate_count,
                # Similarity score
                "similarity_score": similarity,
            }
            items.append(AdWithSimilarity(**ad_dict))

        return items

    except Exception as e:
        logger.error(f"Finding similar ads failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Finding similar ads failed: {str(e)}",
        )


@router.post("/embed-ads", response_model=EmbedAdsResponse)
async def embed_ads(
    db: DbSession,
    request: EmbedAdsRequest,
) -> EmbedAdsResponse:
    """
    Generate embeddings for ads that don't have them.

    This is a batch operation that processes ads with completed analysis
    but no embeddings yet.

    Args:
        request: Parameters including limit on number of ads to process

    Returns:
        Statistics about the embedding process
    """
    try:
        embedding_service = EmbeddingService()

        result = await embedding_service.embed_batch(
            db=db,
            limit=request.limit,
        )

        return EmbedAdsResponse(
            processed=result["processed"],
            failed=result["failed"],
        )

    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch embedding failed: {str(e)}",
        )
