"""Ads API endpoints."""

import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
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
from app.services.ad_library_scraper import AdLibraryScraper, AdLibraryScraperError
from app.services.creative_downloader import CreativeDownloader, CreativeDownloadError
from app.services.image_analyzer import ImageAnalyzer, ImageAnalysisError
from app.services.video_analyzer import VideoAnalyzer, VideoAnalysisError

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


def sanitize_unicode(text: str | None) -> str | None:
    """Remove invalid Unicode surrogates that can't be encoded to UTF-8."""
    if text is None:
        return None
    # Encode with surrogatepass to handle surrogates, then decode back
    # This replaces invalid surrogates with the replacement character
    return text.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")


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
            started_running_date=ad.started_running_date,
            total_active_time=ad.total_active_time,
            platforms=ad.platforms,
            link_headline=ad.link_headline,
            link_description=ad.link_description,
            additional_links=ad.additional_links,
            form_fields=ad.form_fields,
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
        started_running_date=ad.started_running_date,
        total_active_time=ad.total_active_time,
        platforms=ad.platforms,
        link_headline=ad.link_headline,
        link_description=ad.link_description,
        additional_links=ad.additional_links,
        form_fields=ad.form_fields,
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

    max_ads = request.max_ads or settings.max_ads_per_competitor

    # Use browser scraper instead of Graph API
    try:
        scraper = AdLibraryScraper()
        scraped_ads = await scraper.scrape_ads_for_page(
            competitor.page_id,
            max_ads=max_ads,
        )
    except AdLibraryScraperError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to scrape ads from Ad Library: {e}",
        )

    retrieved = 0
    skipped = 0
    failed = 0

    downloader = CreativeDownloader()

    for ad_data in scraped_ads:
        ad_library_id = ad_data.get("ad_library_id")
        if not ad_library_id:
            failed += 1
            continue

        # Ensure ad_library_id is a string for consistent comparison
        ad_library_id = str(ad_library_id)

        # Check if we already have this ad
        existing = await db.execute(
            select(Ad).where(Ad.ad_library_id == ad_library_id)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        # Filter by date if since_days was specified
        if request.since_days and ad_data.get("publication_date"):
            since_date = datetime.utcnow() - timedelta(days=request.since_days)
            if ad_data["publication_date"] < since_date:
                skipped += 1
                continue

        try:
            snapshot_url = ad_data.get("ad_snapshot_url")
            creative_type = ad_data.get("creative_type", "image")

            if snapshot_url:
                storage_path, detected_type = await downloader.download_creative(
                    snapshot_url,
                    competitor.id,
                    ad_library_id,
                )
                download_status = "completed"
                # Use detected type if available
                if detected_type:
                    creative_type = detected_type
            else:
                storage_path = f"pending/{ad_library_id}"
                download_status = "pending"

            # Scrape detailed ad info from modal view (if enabled)
            ad_details = {}
            if request.scrape_details:
                try:
                    ad_details = await scraper.scrape_ad_details(
                        ad_library_id=ad_library_id,
                        page_id=competitor.page_id,
                        country="AU",
                    )
                    logger.info(f"Scraped details for ad {ad_library_id}")
                    # Add delay between detail scrapes to avoid rate limiting
                    await asyncio.sleep(1.5)
                except Exception as e:
                    logger.warning(f"Failed to scrape details for ad {ad_library_id}: {e}")

            db_ad = Ad(
                competitor_id=competitor.id,
                ad_library_id=ad_library_id,
                ad_snapshot_url=snapshot_url,
                creative_type=creative_type,
                creative_storage_path=storage_path,
                # Use detailed ad_copy if available, otherwise fallback to basic scrape
                ad_copy=sanitize_unicode(ad_details.get("primary_text") or ad_data.get("ad_copy")),
                ad_headline=sanitize_unicode(ad_details.get("link_headline") or ad_data.get("ad_headline")),
                ad_description=sanitize_unicode(ad_details.get("link_description") or ad_data.get("ad_description")),
                cta_text=sanitize_unicode(ad_details.get("cta_text") or ad_data.get("cta_text")),
                publication_date=ad_data.get("publication_date"),
                download_status=download_status,
                is_carousel=ad_data.get("is_carousel", False),
                carousel_item_count=ad_data.get("carousel_item_count"),
                landing_page_url=sanitize_unicode(ad_data.get("landing_page_url")),
                is_active=ad_data.get("is_active", True),
                # New detailed fields from modal
                started_running_date=ad_details.get("started_running_date"),
                total_active_time=ad_details.get("total_active_time"),
                platforms=ad_details.get("platforms"),
                link_headline=sanitize_unicode(ad_details.get("link_headline")),
                link_description=sanitize_unicode(ad_details.get("link_description")),
                additional_links=ad_details.get("additional_links"),
                form_fields=ad_details.get("form_fields"),
            )
            # Use savepoint to handle duplicates without rolling back entire transaction
            try:
                async with db.begin_nested():
                    db.add(db_ad)
                    await db.flush()
                retrieved += 1
            except IntegrityError:
                skipped += 1
                logger.debug(f"Ad {ad_library_id} already exists, skipping")

        except CreativeDownloadError as e:
            logger.warning(f"Failed to download creative for ad {ad_library_id}: {e}")
            failed += 1
        except Exception as e:
            logger.warning(f"Failed to process ad {ad_library_id}: {e}")
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
        started_running_date=ad.started_running_date,
        total_active_time=ad.total_active_time,
        platforms=ad.platforms,
        link_headline=ad.link_headline,
        link_description=ad.link_description,
        additional_links=ad.additional_links,
        form_fields=ad.form_fields,
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


@router.post("/{ad_id}/scrape-details", response_model=AdResponse)
async def scrape_ad_details(
    db: DbSession,
    ad_id: UUID,
) -> AdResponse:
    """
    Scrape detailed information for a specific ad from Meta Ad Library.

    Opens the ad details modal and extracts:
    - Started running date and total active time
    - Platforms
    - Link headline and description
    - Additional links
    - Form fields (for lead gen ads)
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

    competitor = ad.competitor
    if not competitor or not competitor.page_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Competitor page_id not available",
        )

    try:
        scraper = AdLibraryScraper()
        details = await scraper.scrape_ad_details(
            ad_library_id=ad.ad_library_id,
            page_id=competitor.page_id,
        )

        # Update ad with scraped details
        if details.get("started_running_date"):
            ad.started_running_date = details["started_running_date"]
        if details.get("total_active_time"):
            ad.total_active_time = details["total_active_time"]
        if details.get("platforms"):
            ad.platforms = details["platforms"]
        if details.get("primary_text") and not ad.ad_copy:
            ad.ad_copy = sanitize_unicode(details["primary_text"])
        if details.get("link_headline"):
            ad.link_headline = sanitize_unicode(details["link_headline"])
        if details.get("link_description"):
            ad.link_description = sanitize_unicode(details["link_description"])
        if details.get("cta_text") and not ad.cta_text:
            ad.cta_text = sanitize_unicode(details["cta_text"])
        if details.get("additional_links"):
            ad.additional_links = details["additional_links"]
        if details.get("form_fields"):
            ad.form_fields = details["form_fields"]

        await db.commit()
        await db.refresh(ad)

    except AdLibraryScraperError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to scrape ad details: {e}",
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
        started_running_date=ad.started_running_date,
        total_active_time=ad.total_active_time,
        platforms=ad.platforms,
        link_headline=ad.link_headline,
        link_description=ad.link_description,
        additional_links=ad.additional_links,
        form_fields=ad.form_fields,
        analysis=ad.analysis,
        retrieved_date=ad.retrieved_date,
        analyzed_date=ad.analyzed_date,
        analyzed=ad.analyzed,
        download_status=ad.download_status,
        analysis_status=ad.analysis_status,
        total_engagement=ad.total_engagement,
        overall_score=ad.overall_score,
    )
