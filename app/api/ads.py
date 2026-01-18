"""Ads API endpoints."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.config import get_settings
from app.models.ad import Ad
from app.models.competitor import Competitor
from app.schemas.ad import (
    AdListResponse,
    AdResponse,
    AdRetrieveRequest,
    AdRetrieveResponse,
    AdStats,
)
from app.services.creative_downloader import CreativeDownloader, CreativeDownloadError
from app.services.image_analyzer import ImageAnalyzer, ImageAnalysisError
from app.services.meta_ad_library import MetaAdLibraryClient, MetaAdLibraryError
from app.services.video_analyzer import VideoAnalyzer, VideoAnalysisError

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.get("", response_model=AdListResponse)
async def list_ads(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    competitor_id: UUID | None = None,
    analyzed: bool | None = None,
    creative_type: str | None = None,
    min_engagement: int | None = None,
) -> AdListResponse:
    """List ads with filtering and pagination."""
    query = select(Ad).options(selectinload(Ad.competitor))

    filters = []
    if competitor_id:
        filters.append(Ad.competitor_id == competitor_id)
    if analyzed is not None:
        filters.append(Ad.analyzed == analyzed)
    if creative_type:
        filters.append(Ad.creative_type == creative_type)
    if min_engagement:
        filters.append((Ad.likes + Ad.comments + Ad.shares) >= min_engagement)

    if filters:
        query = query.where(and_(*filters))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Ad.publication_date.desc().nullslast())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    ads = result.scalars().all()

    items = []
    for ad in ads:
        ad_response = AdResponse(
            id=ad.id,
            competitor_id=ad.competitor_id,
            ad_library_id=ad.ad_library_id,
            ad_snapshot_url=ad.ad_snapshot_url,
            creative_type=ad.creative_type,
            creative_storage_path=ad.creative_storage_path,
            creative_url=ad.creative_url,
            ad_copy=ad.ad_copy,
            ad_headline=ad.ad_headline,
            ad_description=ad.ad_description,
            cta_text=ad.cta_text,
            likes=ad.likes,
            comments=ad.comments,
            shares=ad.shares,
            impressions=ad.impressions,
            publication_date=ad.publication_date,
            analysis=ad.analysis,
            retrieved_date=ad.retrieved_date,
            analyzed_date=ad.analyzed_date,
            analyzed=ad.analyzed,
            download_status=ad.download_status,
            analysis_status=ad.analysis_status,
            total_engagement=ad.total_engagement,
            overall_score=ad.overall_score,
        )
        items.append(ad_response)

    return AdListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=AdStats)
async def get_ad_stats(
    db: DbSession,
    competitor_id: UUID | None = None,
) -> AdStats:
    """Get ad statistics."""
    base_query = select(Ad)
    if competitor_id:
        base_query = base_query.where(Ad.competitor_id == competitor_id)

    total = (await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )).scalar() or 0

    analyzed = (await db.execute(
        select(func.count()).where(
            and_(Ad.analyzed == True, Ad.competitor_id == competitor_id) if competitor_id
            else Ad.analyzed == True
        )
    )).scalar() or 0

    pending = (await db.execute(
        select(func.count()).where(
            and_(Ad.analysis_status == "pending", Ad.competitor_id == competitor_id) if competitor_id
            else Ad.analysis_status == "pending"
        )
    )).scalar() or 0

    failed = (await db.execute(
        select(func.count()).where(
            and_(Ad.analysis_status == "failed", Ad.competitor_id == competitor_id) if competitor_id
            else Ad.analysis_status == "failed"
        )
    )).scalar() or 0

    type_counts_query = select(Ad.creative_type, func.count().label("count"))
    if competitor_id:
        type_counts_query = type_counts_query.where(Ad.competitor_id == competitor_id)
    type_counts_query = type_counts_query.group_by(Ad.creative_type)
    type_results = await db.execute(type_counts_query)
    by_type = {row.creative_type: row.count for row in type_results}

    avg_eng_query = select(func.avg(Ad.likes + Ad.comments + Ad.shares))
    if competitor_id:
        avg_eng_query = avg_eng_query.where(Ad.competitor_id == competitor_id)
    avg_engagement = (await db.execute(avg_eng_query)).scalar() or 0.0

    top_performer_query = select(Ad.id).where(Ad.analyzed == True)
    if competitor_id:
        top_performer_query = top_performer_query.where(Ad.competitor_id == competitor_id)
    top_performer_query = top_performer_query.order_by(
        (Ad.likes + Ad.comments + Ad.shares).desc()
    ).limit(1)
    top_performer = (await db.execute(top_performer_query)).scalar()

    return AdStats(
        total_ads=total,
        analyzed_ads=analyzed,
        pending_analysis=pending,
        failed_analysis=failed,
        by_type=by_type,
        avg_engagement=float(avg_engagement),
        avg_score=None,
        top_performer_id=top_performer,
    )


@router.get("/{ad_id}", response_model=AdResponse)
async def get_ad(
    db: DbSession,
    ad_id: UUID,
) -> AdResponse:
    """Get a single ad by ID."""
    result = await db.execute(
        select(Ad).options(selectinload(Ad.competitor)).where(Ad.id == ad_id)
    )
    ad = result.scalar_one_or_none()

    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found",
        )

    return AdResponse(
        id=ad.id,
        competitor_id=ad.competitor_id,
        ad_library_id=ad.ad_library_id,
        ad_snapshot_url=ad.ad_snapshot_url,
        creative_type=ad.creative_type,
        creative_storage_path=ad.creative_storage_path,
        creative_url=ad.creative_url,
        ad_copy=ad.ad_copy,
        ad_headline=ad.ad_headline,
        ad_description=ad.ad_description,
        cta_text=ad.cta_text,
        likes=ad.likes,
        comments=ad.comments,
        shares=ad.shares,
        impressions=ad.impressions,
        publication_date=ad.publication_date,
        analysis=ad.analysis,
        retrieved_date=ad.retrieved_date,
        analyzed_date=ad.analyzed_date,
        analyzed=ad.analyzed,
        download_status=ad.download_status,
        analysis_status=ad.analysis_status,
        total_engagement=ad.total_engagement,
        overall_score=ad.overall_score,
    )


@router.post("/retrieve", response_model=AdRetrieveResponse)
async def retrieve_ads(
    db: DbSession,
    request: AdRetrieveRequest,
) -> AdRetrieveResponse:
    """
    Retrieve ads from Meta Ad Library for a competitor.

    This downloads new ads and stores them in the database.
    """
    result = await db.execute(
        select(Competitor).where(Competitor.id == request.competitor_id)
    )
    competitor = result.scalar_one_or_none()

    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )

    since_date = None
    if request.since_days:
        since_date = datetime.utcnow() - timedelta(days=request.since_days)
    elif competitor.last_retrieved:
        since_date = competitor.last_retrieved

    max_ads = request.max_ads or settings.max_ads_per_competitor

    try:
        meta_client = MetaAdLibraryClient()
        raw_ads = await meta_client.get_ads_for_competitor(
            competitor.ad_library_url,
            since_date=since_date,
            limit=max_ads,
        )
    except MetaAdLibraryError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to retrieve ads from Meta: {e}",
        )

    retrieved = 0
    skipped = 0
    failed = 0

    downloader = CreativeDownloader()

    for raw_ad in raw_ads:
        parsed = meta_client.parse_ad_data(raw_ad)

        existing = await db.execute(
            select(Ad).where(Ad.ad_library_id == parsed["ad_library_id"])
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        try:
            snapshot_url = parsed.get("ad_snapshot_url")
            if snapshot_url:
                storage_path, creative_type = await downloader.download_creative(
                    snapshot_url,
                    competitor.id,
                    parsed["ad_library_id"],
                )
                download_status = "completed"
            else:
                storage_path = f"pending/{parsed['ad_library_id']}"
                creative_type = "image"
                download_status = "pending"

            db_ad = Ad(
                competitor_id=competitor.id,
                ad_library_id=parsed["ad_library_id"],
                ad_snapshot_url=snapshot_url,
                creative_type=creative_type,
                creative_storage_path=storage_path,
                creative_url=parsed.get("creative_url"),
                ad_copy=parsed.get("ad_copy"),
                ad_headline=parsed.get("ad_headline"),
                ad_description=parsed.get("ad_description"),
                cta_text=parsed.get("cta_text"),
                publication_date=parsed.get("publication_date"),
                download_status=download_status,
            )
            db.add(db_ad)
            retrieved += 1

        except CreativeDownloadError as e:
            logger.warning(f"Failed to download creative for ad {parsed['ad_library_id']}: {e}")
            failed += 1

    competitor.last_retrieved = datetime.utcnow()
    await db.commit()

    return AdRetrieveResponse(
        retrieved=retrieved,
        skipped=skipped,
        failed=failed,
        competitor_id=competitor.id,
    )


@router.post("/analyze/{ad_id}", response_model=AdResponse)
async def analyze_ad(
    db: DbSession,
    ad_id: UUID,
) -> AdResponse:
    """
    Analyze a single ad using AI.

    Uses GPT-4 Vision for images and Gemini for videos.
    """
    result = await db.execute(
        select(Ad).options(selectinload(Ad.competitor)).where(Ad.id == ad_id)
    )
    ad = result.scalar_one_or_none()

    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found",
        )

    if ad.download_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ad creative has not been downloaded yet",
        )

    competitor = ad.competitor

    try:
        if ad.creative_type == "image":
            analyzer = ImageAnalyzer()
            analysis = await analyzer.analyze_from_storage(
                ad.creative_storage_path,
                competitor_name=competitor.company_name,
                market_position=competitor.market_position,
                follower_count=competitor.follower_count,
                likes=ad.likes,
                comments=ad.comments,
                shares=ad.shares,
            )
        else:
            analyzer = VideoAnalyzer()
            analysis = await analyzer.analyze_from_storage(
                ad.creative_storage_path,
                competitor_name=competitor.company_name,
                market_position=competitor.market_position,
                follower_count=competitor.follower_count,
                likes=ad.likes,
                comments=ad.comments,
                shares=ad.shares,
            )

        ad.analysis = analysis
        ad.analyzed = True
        ad.analyzed_date = datetime.utcnow()
        ad.analysis_status = "completed"

    except (ImageAnalysisError, VideoAnalysisError) as e:
        ad.analysis_status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {e}",
        )

    await db.commit()
    await db.refresh(ad)

    return AdResponse(
        id=ad.id,
        competitor_id=ad.competitor_id,
        ad_library_id=ad.ad_library_id,
        ad_snapshot_url=ad.ad_snapshot_url,
        creative_type=ad.creative_type,
        creative_storage_path=ad.creative_storage_path,
        creative_url=ad.creative_url,
        ad_copy=ad.ad_copy,
        ad_headline=ad.ad_headline,
        ad_description=ad.ad_description,
        cta_text=ad.cta_text,
        likes=ad.likes,
        comments=ad.comments,
        shares=ad.shares,
        impressions=ad.impressions,
        publication_date=ad.publication_date,
        analysis=ad.analysis,
        retrieved_date=ad.retrieved_date,
        analyzed_date=ad.analyzed_date,
        analyzed=ad.analyzed,
        download_status=ad.download_status,
        analysis_status=ad.analysis_status,
        total_engagement=ad.total_engagement,
        overall_score=ad.overall_score,
    )


@router.post("/analyze/run")
async def run_analysis(
    db: DbSession,
    limit: int = Query(10, ge=1, le=100),
) -> dict:
    """
    Run analysis on unanalyzed ads.

    Processes ads in batches, analyzing up to `limit` ads.
    """
    result = await db.execute(
        select(Ad)
        .options(selectinload(Ad.competitor))
        .where(
            and_(
                Ad.analyzed == False,
                Ad.download_status == "completed",
                Ad.analysis_status == "pending",
            )
        )
        .limit(limit)
    )
    ads = result.scalars().all()

    processed = 0
    failed = 0

    image_analyzer = ImageAnalyzer()
    video_analyzer = VideoAnalyzer()

    for ad in ads:
        competitor = ad.competitor
        try:
            if ad.creative_type == "image":
                analysis = await image_analyzer.analyze_from_storage(
                    ad.creative_storage_path,
                    competitor_name=competitor.company_name,
                    market_position=competitor.market_position,
                    follower_count=competitor.follower_count,
                    likes=ad.likes,
                    comments=ad.comments,
                    shares=ad.shares,
                )
            else:
                analysis = await video_analyzer.analyze_from_storage(
                    ad.creative_storage_path,
                    competitor_name=competitor.company_name,
                    market_position=competitor.market_position,
                    follower_count=competitor.follower_count,
                    likes=ad.likes,
                    comments=ad.comments,
                    shares=ad.shares,
                )

            ad.analysis = analysis
            ad.analyzed = True
            ad.analyzed_date = datetime.utcnow()
            ad.analysis_status = "completed"
            processed += 1

        except Exception as e:
            logger.error(f"Failed to analyze ad {ad.id}: {e}")
            ad.analysis_status = "failed"
            failed += 1

    await db.commit()

    return {
        "processed": processed,
        "failed": failed,
        "total_attempted": len(ads),
    }
