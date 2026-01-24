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
from app.services.creative_analysis_service import populate_from_video_intelligence
from app.services.creative_downloader import CreativeDownloader, CreativeDownloadError
from app.services.duplicate_detection import DuplicateDetector
from app.services.image_analyzer import ImageAnalyzer, ImageAnalysisError
from app.services.video_analyzer import VideoAnalyzer, VideoAnalysisError
from app.services.composite_scoring_service import CompositeScoreCalculator
from app.api.notifications import create_new_ads_notification
from app.schemas.search import ScoreCalculationResponse, PercentileRecalculationResponse

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
    min_overall_score: float | None = Query(None, ge=0, le=10, description="Minimum overall marketing score (1-10)"),
    min_composite_score: float | None = Query(None, ge=0, le=1, description="Minimum composite score (0-1)"),
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
    if min_composite_score is not None:
        filters.append(Ad.composite_score >= min_composite_score)
    # For overall_score, we need to filter using JSON path since it's nested in analysis
    # Note: We'll filter this in Python after query for simplicity, or use JSON operators

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
        # Apply overall_score filter in Python (since it's nested in JSONB)
        if min_overall_score is not None:
            ad_overall_score = ad.overall_score
            if ad_overall_score is None or ad_overall_score < min_overall_score:
                continue

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
            video_intelligence=ad.video_intelligence,
            retrieved_date=ad.retrieved_date,
            analyzed_date=ad.analyzed_date,
            analyzed=ad.analyzed,
            download_status=ad.download_status,
            analysis_status=ad.analysis_status,
            total_engagement=ad.total_engagement,
            overall_score=ad.overall_score,
            composite_score=ad.composite_score,
            engagement_rate_percentile=ad.engagement_rate_percentile,
            survivorship_score=ad.survivorship_score,
            ad_summary=ad.ad_summary,
            original_ad_id=ad.original_ad_id,
            duplicate_count=ad.duplicate_count,
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
        video_intelligence=ad.video_intelligence,
        retrieved_date=ad.retrieved_date,
        analyzed_date=ad.analyzed_date,
        analyzed=ad.analyzed,
        download_status=ad.download_status,
        analysis_status=ad.analysis_status,
        total_engagement=ad.total_engagement,
        overall_score=ad.overall_score,
        composite_score=ad.composite_score,
        engagement_rate_percentile=ad.engagement_rate_percentile,
        survivorship_score=ad.survivorship_score,
        ad_summary=ad.ad_summary,
        original_ad_id=ad.original_ad_id,
        duplicate_count=ad.duplicate_count,
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
    duplicates_found = 0

    downloader = CreativeDownloader()
    duplicate_detector = DuplicateDetector()

    for ad_data in scraped_ads:
        ad_library_id = ad_data.get("ad_library_id")
        if not ad_library_id:
            failed += 1
            continue

        # Ensure ad_library_id is a string for consistent comparison
        ad_library_id = str(ad_library_id)

        # Check if we already have this ad (by ad_library_id)
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
            creative_url = ad_data.get("creative_url")  # Direct URL from embedded JSON
            creative_type = ad_data.get("creative_type", "image")

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

            # --- DUPLICATE DETECTION ---
            # Check if this creative already exists (by perceptual hash)
            original_ad = None
            perceptual_hash = None

            if creative_url:
                # Compute hash from URL without downloading full file yet
                perceptual_hash = await duplicate_detector.get_phash_from_url(
                    creative_url, creative_type
                )
                if perceptual_hash:
                    # Look for existing original with matching hash
                    original_ad = await duplicate_detector.find_original_by_hash(
                        db, perceptual_hash, creative_type
                    )

            if original_ad:
                # --- DUPLICATE PATH ---
                # Create minimal record referencing the original (no download needed)
                logger.info(
                    f"Duplicate detected: ad {ad_library_id} matches original {original_ad.id}"
                )
                db_ad = Ad(
                    competitor_id=competitor.id,
                    ad_library_id=ad_library_id,
                    ad_snapshot_url=snapshot_url,
                    creative_type=creative_type,
                    creative_storage_path="",  # Empty - use original's storage
                    creative_url=creative_url,
                    original_ad_id=original_ad.id,  # Link to original
                    # Text fields (may differ from original)
                    ad_copy=sanitize_unicode(ad_details.get("primary_text") or ad_data.get("ad_copy")),
                    ad_headline=sanitize_unicode(ad_details.get("link_headline") or ad_data.get("ad_headline")),
                    ad_description=sanitize_unicode(ad_details.get("link_description") or ad_data.get("ad_description")),
                    cta_text=sanitize_unicode(ad_details.get("cta_text") or ad_data.get("cta_text")),
                    publication_date=ad_data.get("publication_date"),
                    download_status="completed",  # Nothing to download
                    is_carousel=ad_data.get("is_carousel", False),
                    carousel_item_count=ad_data.get("carousel_item_count"),
                    landing_page_url=sanitize_unicode(ad_data.get("landing_page_url")),
                    is_active=ad_data.get("is_active", True),
                    likes=ad_data.get("likes", 0),
                    comments=ad_data.get("comments", 0),
                    shares=ad_data.get("shares", 0),
                    # Detailed fields from modal
                    started_running_date=ad_details.get("started_running_date"),
                    total_active_time=ad_details.get("total_active_time"),
                    platforms=ad_details.get("platforms"),
                    link_headline=sanitize_unicode(ad_details.get("link_headline")),
                    link_description=sanitize_unicode(ad_details.get("link_description")),
                    additional_links=ad_details.get("additional_links"),
                    form_fields=ad_details.get("form_fields"),
                )
                # Increment duplicate count on original
                original_ad.duplicate_count += 1
                duplicates_found += 1

            else:
                # --- ORIGINAL PATH ---
                # Download the creative and store it
                if creative_url or snapshot_url:
                    storage_path, detected_type, extracted_url = await downloader.download_creative(
                        snapshot_url,
                        competitor.id,
                        ad_library_id,
                        creative_url=creative_url,
                    )
                    download_status = "completed"
                    if detected_type:
                        creative_type = detected_type
                    if extracted_url:
                        creative_url = extracted_url
                    # Compute hash if we didn't have creative_url before
                    if not perceptual_hash and creative_url:
                        perceptual_hash = await duplicate_detector.get_phash_from_url(
                            creative_url, creative_type
                        )
                else:
                    storage_path = f"pending/{ad_library_id}"
                    download_status = "pending"

                db_ad = Ad(
                    competitor_id=competitor.id,
                    ad_library_id=ad_library_id,
                    ad_snapshot_url=snapshot_url,
                    creative_type=creative_type,
                    creative_storage_path=storage_path,
                    creative_url=creative_url,
                    perceptual_hash=perceptual_hash,  # Store hash for future dedup
                    duplicate_count=1,  # This is an original
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
                    likes=ad_data.get("likes", 0),
                    comments=ad_data.get("comments", 0),
                    shares=ad_data.get("shares", 0),
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

    # Clean up duplicate detector HTTP client
    await duplicate_detector.close()

    competitor.last_retrieved = datetime.utcnow()
    await db.commit()

    # Create notification if new ads were retrieved
    if retrieved > 0:
        try:
            await create_new_ads_notification(
                db=db,
                competitor_id=competitor.id,
                competitor_name=competitor.company_name,
                ad_count=retrieved,
            )
        except Exception as e:
            logger.warning(f"Failed to create notification for new ads: {e}")

    return AdRetrieveResponse(
        retrieved=retrieved,
        skipped=skipped,
        failed=failed,
        competitor_id=competitor.id,
    )


@router.post("/analyze/run")
async def run_analysis(
    db: DbSession,
    limit: int = Query(10, ge=1, le=100),
    skip_duplicate_check: bool = Query(False, description="Skip the original_ad_id check to process all unanalyzed ads"),
) -> dict:
    """
    Run analysis on unanalyzed ads using V2 Enhanced Analysis.

    Processes ads in batches, analyzing up to `limit` ads.
    Only analyzes ORIGINAL ads (not duplicates) and propagates results to duplicates.

    Returns EnhancedAdAnalysisV2 with:
    - Creative DNA (text/copy, audio, brand elements)
    - Engagement predictors (thumb-stop, curiosity gap)
    - Platform optimization signals
    - Actionable critique with grades and suggestions
    - Timestamped narrative beats (video only)

    Use skip_duplicate_check=true to process ads regardless of original_ad_id status.
    """
    # Build filter conditions
    filters = [
        Ad.analyzed == False,
        Ad.download_status == "completed",
        Ad.analysis_status.in_(["pending", "failed"]),
    ]

    # Only filter by original_ad_id if not skipping the check
    if not skip_duplicate_check:
        filters.append(Ad.original_ad_id.is_(None))  # Only originals, not duplicates

    result = await db.execute(
        select(Ad)
        .options(selectinload(Ad.competitor))
        .where(and_(*filters))
        .limit(limit)
    )
    ads = result.scalars().all()

    logger.info(f"Found {len(ads)} ads to analyze")

    processed = 0
    failed = 0
    duplicates_updated = 0

    image_analyzer = ImageAnalyzer()
    video_analyzer = VideoAnalyzer()

    for ad in ads:
        competitor = ad.competitor
        try:
            if ad.creative_type == "image":
                # Use V2 enhanced image analysis
                raw_analysis = await image_analyzer.analyze_from_storage_v2(
                    ad.creative_storage_path,
                    competitor_name=competitor.company_name,
                    market_position=competitor.market_position,
                    follower_count=competitor.follower_count,
                    likes=ad.likes,
                    comments=ad.comments,
                    shares=ad.shares,
                    platform_cta=ad.cta_text,
                )
                # Parse into EnhancedAdAnalysisV2 model
                enhanced_analysis = image_analyzer.parse_enhanced_analysis_v2(raw_analysis)
                # Get serializable dict for JSONB storage
                video_intelligence = image_analyzer.get_image_intelligence_v2(enhanced_analysis)
            else:
                # Use V2 enhanced video analysis
                raw_analysis = await video_analyzer.analyze_from_storage_v2(
                    ad.creative_storage_path,
                    competitor_name=competitor.company_name,
                    market_position=competitor.market_position,
                    follower_count=competitor.follower_count,
                    likes=ad.likes,
                    comments=ad.comments,
                    shares=ad.shares,
                    platform_cta=ad.cta_text,
                )
                # Parse into EnhancedAdAnalysisV2 model
                enhanced_analysis = video_analyzer.parse_enhanced_analysis_v2(raw_analysis)
                # Get serializable dict for JSONB storage
                video_intelligence = video_analyzer.get_video_intelligence_v2(enhanced_analysis)

            # Store the full V2 Creative DNA in video_intelligence column
            ad.video_intelligence = video_intelligence

            # Create backward-compatible analysis dict for legacy consumers
            hook_score = video_intelligence.get("hook_score", 5)
            pacing_score = video_intelligence.get("overall_pacing_score", 5)
            critique = video_intelligence.get("critique", {})
            analysis = {
                "summary": video_intelligence.get("overall_narrative_summary", ""),
                "insights": [],
                "uvps": [],
                "ctas": [],
                "visual_themes": [],
                "target_audience": video_intelligence.get("inferred_audience", ""),
                "emotional_appeal": video_intelligence.get("primary_messaging_pillar", ""),
                "marketing_effectiveness": {
                    "hook_strength": hook_score,
                    "message_clarity": pacing_score,
                    "visual_impact": pacing_score,
                    "cta_effectiveness": 5,
                    "overall_score": pacing_score,
                },
                "strategic_insights": f"Production Style: {video_intelligence.get('production_style', 'Unknown')}",
                "reasoning": critique.get("overall_assessment", video_intelligence.get("overall_narrative_summary", "")),
                "video_analysis": {
                    "pacing": f"Pacing score: {pacing_score}/10",
                    "audio_strategy": "",
                    "story_arc": video_intelligence.get("overall_narrative_summary", ""),
                    "caption_usage": "",
                    "optimal_length": "",
                },
                "grade": critique.get("overall_grade", ""),
            }
            ad.analysis = analysis

            ad.analyzed = True
            ad.analyzed_date = datetime.utcnow()
            ad.analysis_status = "completed"
            processed += 1

            # Populate ad_creative_analysis and ad_elements tables
            await populate_from_video_intelligence(db, ad, video_intelligence)

            # Propagate analysis to ALL duplicates of this original
            update_values = {
                "analysis": analysis,
                "video_intelligence": video_intelligence,
                "analyzed": True,
                "analyzed_date": datetime.utcnow(),
                "analysis_status": "completed",
            }

            update_result = await db.execute(
                Ad.__table__.update()
                .where(Ad.original_ad_id == ad.id)
                .values(**update_values)
            )
            duplicates_updated += update_result.rowcount

            # Note: Duplicates will have their creative_analysis/elements populated
            # when they are individually analyzed or via backfill

        except Exception as e:
            logger.error(f"Failed to analyze ad {ad.id}: {e}")
            ad.analysis_status = "failed"
            failed += 1

    await db.commit()

    return {
        "processed": processed,
        "failed": failed,
        "duplicates_updated": duplicates_updated,
        "total_attempted": len(ads),
    }


@router.post("/analyze/{ad_id}", response_model=AdResponse)
async def analyze_ad(
    db: DbSession,
    ad_id: UUID,
) -> AdResponse:
    """
    Analyze a single ad using V2 Enhanced Analysis.

    Uses GPT-4o for images and Gemini 2.0 Flash for videos.
    If the ad is a duplicate, copies analysis from the original instead of re-analyzing.

    Returns EnhancedAdAnalysisV2 with:
    - Creative DNA (text/copy, audio, brand elements)
    - Engagement predictors (thumb-stop, curiosity gap)
    - Platform optimization signals
    - Actionable critique with grades and suggestions
    - Timestamped narrative beats (video only)
    """
    result = await db.execute(
        select(Ad).options(selectinload(Ad.competitor), selectinload(Ad.original_ad)).where(Ad.id == ad_id)
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

    # --- DUPLICATE HANDLING ---
    # If this ad is a duplicate, use the original's analysis
    if ad.original_ad_id:
        original_ad = ad.original_ad
        if not original_ad:
            # Fetch original if not loaded
            result = await db.execute(
                select(Ad).options(selectinload(Ad.competitor)).where(Ad.id == ad.original_ad_id)
            )
            original_ad = result.scalar_one_or_none()

        if original_ad and original_ad.analysis:
            # Copy analysis from original (no LLM call needed)
            logger.info(f"Copying analysis from original ad {original_ad.id} to duplicate {ad.id}")
            ad.analysis = original_ad.analysis
            ad.video_intelligence = original_ad.video_intelligence
            ad.analyzed = True
            ad.analyzed_date = datetime.utcnow()
            ad.analysis_status = "completed"
            # Populate creative_analysis and elements for this duplicate
            if ad.video_intelligence:
                await populate_from_video_intelligence(db, ad)
            await db.commit()
            await db.refresh(ad)
            return _build_ad_response(ad)

        # Original exists but not analyzed - analyze the original instead
        if original_ad:
            ad_to_analyze = original_ad
            competitor = original_ad.competitor
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Original ad not found for this duplicate",
            )
    else:
        # This is an original ad - analyze it directly
        ad_to_analyze = ad
        competitor = ad.competitor

    # --- V2 ENHANCED ANALYSIS ---
    try:
        if ad_to_analyze.creative_type == "image":
            # Use V2 enhanced image analysis
            image_analyzer = ImageAnalyzer()
            raw_analysis = await image_analyzer.analyze_from_storage_v2(
                ad_to_analyze.creative_storage_path,
                competitor_name=competitor.company_name,
                market_position=competitor.market_position,
                follower_count=competitor.follower_count,
                likes=ad_to_analyze.likes,
                comments=ad_to_analyze.comments,
                shares=ad_to_analyze.shares,
                platform_cta=ad_to_analyze.cta_text,
            )
            # Parse into EnhancedAdAnalysisV2 model
            enhanced_analysis = image_analyzer.parse_enhanced_analysis_v2(raw_analysis)
            # Get serializable dict for JSONB storage
            video_intelligence = image_analyzer.get_image_intelligence_v2(enhanced_analysis)
        else:
            # Use V2 enhanced video analysis
            video_analyzer = VideoAnalyzer()
            raw_analysis = await video_analyzer.analyze_from_storage_v2(
                ad_to_analyze.creative_storage_path,
                competitor_name=competitor.company_name,
                market_position=competitor.market_position,
                follower_count=competitor.follower_count,
                likes=ad_to_analyze.likes,
                comments=ad_to_analyze.comments,
                shares=ad_to_analyze.shares,
                platform_cta=ad_to_analyze.cta_text,
            )
            # Parse into EnhancedAdAnalysisV2 model
            enhanced_analysis = video_analyzer.parse_enhanced_analysis_v2(raw_analysis)
            # Get serializable dict for JSONB storage
            video_intelligence = video_analyzer.get_video_intelligence_v2(enhanced_analysis)

        # Store the full V2 Creative DNA in video_intelligence column
        ad_to_analyze.video_intelligence = video_intelligence

        # Create backward-compatible analysis dict for legacy consumers
        hook_score = video_intelligence.get("hook_score", 5)
        pacing_score = video_intelligence.get("overall_pacing_score", 5)
        critique = video_intelligence.get("critique", {})
        analysis = {
            "summary": video_intelligence.get("overall_narrative_summary", ""),
            "insights": [],
            "uvps": [],
            "ctas": [],
            "visual_themes": [],
            "target_audience": video_intelligence.get("inferred_audience", ""),
            "emotional_appeal": video_intelligence.get("primary_messaging_pillar", ""),
            "marketing_effectiveness": {
                "hook_strength": hook_score,
                "message_clarity": pacing_score,
                "visual_impact": pacing_score,
                "cta_effectiveness": 5,
                "overall_score": pacing_score,
            },
            "strategic_insights": f"Production Style: {video_intelligence.get('production_style', 'Unknown')}",
            "reasoning": critique.get("overall_assessment", video_intelligence.get("overall_narrative_summary", "")),
            "video_analysis": {
                "pacing": f"Pacing score: {pacing_score}/10",
                "audio_strategy": "",
                "story_arc": video_intelligence.get("overall_narrative_summary", ""),
                "caption_usage": "",
                "optimal_length": "",
            },
            "grade": critique.get("overall_grade", ""),
        }

        # Update the analyzed ad (original)
        ad_to_analyze.analysis = analysis
        ad_to_analyze.analyzed = True
        ad_to_analyze.analyzed_date = datetime.utcnow()
        ad_to_analyze.analysis_status = "completed"

        # Populate ad_creative_analysis and ad_elements tables
        await populate_from_video_intelligence(db, ad_to_analyze, video_intelligence)

        # If we analyzed the original for a duplicate request, also update the duplicate
        if ad.original_ad_id and ad_to_analyze.id != ad.id:
            ad.analysis = analysis
            ad.video_intelligence = video_intelligence
            ad.analyzed = True
            ad.analyzed_date = datetime.utcnow()
            ad.analysis_status = "completed"
            # Also populate for the duplicate
            await populate_from_video_intelligence(db, ad, video_intelligence)

        # Propagate analysis to ALL duplicates of this original
        update_values = {
            "analysis": analysis,
            "video_intelligence": video_intelligence,
            "analyzed": True,
            "analyzed_date": datetime.utcnow(),
            "analysis_status": "completed",
        }

        await db.execute(
            Ad.__table__.update()
            .where(Ad.original_ad_id == ad_to_analyze.id)
            .values(**update_values)
        )

    except (ImageAnalysisError, VideoAnalysisError) as e:
        ad.analysis_status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {e}",
        )

    await db.commit()
    await db.refresh(ad)

    return _build_ad_response(ad)


def _build_ad_response(ad: Ad) -> AdResponse:
    """Build AdResponse from Ad model."""
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
        video_intelligence=ad.video_intelligence,
        retrieved_date=ad.retrieved_date,
        analyzed_date=ad.analyzed_date,
        analyzed=ad.analyzed,
        download_status=ad.download_status,
        analysis_status=ad.analysis_status,
        total_engagement=ad.total_engagement,
        overall_score=ad.overall_score,
        original_ad_id=ad.original_ad_id,
        duplicate_count=ad.duplicate_count,
    )


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
        video_intelligence=ad.video_intelligence,
        retrieved_date=ad.retrieved_date,
        analyzed_date=ad.analyzed_date,
        analyzed=ad.analyzed,
        download_status=ad.download_status,
        analysis_status=ad.analysis_status,
        total_engagement=ad.total_engagement,
        overall_score=ad.overall_score,
        composite_score=ad.composite_score,
        engagement_rate_percentile=ad.engagement_rate_percentile,
        survivorship_score=ad.survivorship_score,
        ad_summary=ad.ad_summary,
        original_ad_id=ad.original_ad_id,
        duplicate_count=ad.duplicate_count,
    )

@router.post("/calculate-scores", response_model=ScoreCalculationResponse)
async def calculate_composite_scores(
    db: DbSession,
    limit: int = Query(100, ge=1, le=1000),
) -> ScoreCalculationResponse:
    """Calculate composite scores for analyzed ads without scores."""
    try:
        score_calculator = CompositeScoreCalculator()

        result = await db.execute(
            select(Ad)
            .options(selectinload(Ad.competitor), selectinload(Ad.creative_analysis))
            .where(
                Ad.analyzed == True,  # noqa: E712
                Ad.analysis_status == "completed",
                Ad.composite_score.is_(None),
            )
            .limit(limit)
        )
        ads = result.scalars().all()

        if not ads:
            return ScoreCalculationResponse(processed=0, failed=0)

        processed = 0
        failed = 0

        for ad in ads:
            try:
                await score_calculator.calculate_composite_score(db, ad)
                processed += 1
                if processed % 10 == 0:
                    await db.commit()
            except Exception as e:
                logger.error(f"Failed to calculate score for ad {ad.id}: {e}")
                failed += 1

        await db.commit()
        return ScoreCalculationResponse(processed=processed, failed=failed)

    except Exception as e:
        logger.error(f"Score calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Score calculation failed: {str(e)}",
        )


@router.post("/recalculate-percentiles", response_model=PercentileRecalculationResponse)
async def recalculate_engagement_percentiles(db: DbSession) -> PercentileRecalculationResponse:
    """Recalculate engagement percentiles for all ads."""
    try:
        score_calculator = CompositeScoreCalculator()
        result = await score_calculator.recalculate_all_percentiles(db)
        return PercentileRecalculationResponse(
            processed=result["processed"],
            skipped=result["skipped"],
        )
    except Exception as e:
        logger.error(f"Percentile recalculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Percentile recalculation failed: {str(e)}",
        )


@router.get("/top-performers", response_model=AdListResponse)
async def get_top_performers(
    db: DbSession,
    limit: int = Query(10, ge=1, le=50),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
) -> AdListResponse:
    """Get top-performing ads by composite score."""
    try:
        result = await db.execute(
            select(Ad)
            .where(Ad.composite_score.isnot(None), Ad.composite_score >= min_score)
            .order_by(Ad.composite_score.desc())
            .limit(limit)
        )
        ads = result.scalars().all()

        items = [
            AdResponse(
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
                video_intelligence=ad.video_intelligence,
                retrieved_date=ad.retrieved_date,
                analyzed_date=ad.analyzed_date,
                analyzed=ad.analyzed,
                download_status=ad.download_status,
                analysis_status=ad.analysis_status,
                total_engagement=ad.total_engagement,
                overall_score=ad.overall_score,
                composite_score=ad.composite_score,
                engagement_rate_percentile=ad.engagement_rate_percentile,
                survivorship_score=ad.survivorship_score,
                ad_summary=ad.ad_summary,
                original_ad_id=ad.original_ad_id,
                duplicate_count=ad.duplicate_count,
            )
            for ad in ads
        ]

        return AdListResponse(items=items, total=len(items), page=1, page_size=limit)

    except Exception as e:
        logger.error(f"Getting top performers failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting top performers failed: {str(e)}",
        )
