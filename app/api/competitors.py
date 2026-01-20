"""Competitors API endpoints."""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession
from app.models.ad import Ad
from app.models.competitor import Competitor
from app.schemas.competitor import (
    CompetitorCreate,
    CompetitorDiscoverRequest,
    CompetitorDiscoverResponse,
    CompetitorListResponse,
    CompetitorResponse,
    CompetitorUpdate,
)
from app.services.competitor_discovery import CompetitorDiscovery, CompetitorDiscoveryError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=CompetitorListResponse)
async def list_competitors(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
) -> CompetitorListResponse:
    """List all competitors with pagination."""
    query = select(Competitor)
    if active_only:
        query = query.where(Competitor.active == True)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Competitor.discovered_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    competitors = result.scalars().all()

    items = []
    for comp in competitors:
        ad_count = (
            await db.execute(
                select(func.count()).where(Ad.competitor_id == comp.id)
            )
        ).scalar() or 0

        comp_response = CompetitorResponse.model_validate(comp)
        comp_response.ad_count = ad_count
        items.append(comp_response)

    return CompetitorListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/add", response_model=CompetitorResponse)
async def add_competitor(
    db: DbSession,
    competitor: CompetitorCreate,
) -> CompetitorResponse:
    """Manually add a competitor."""
    existing = await db.execute(
        select(Competitor).where(Competitor.page_id == competitor.page_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Competitor with this Page ID already exists",
        )

    db_competitor = Competitor(
        company_name=competitor.company_name,
        page_id=competitor.page_id,
        industry=competitor.industry,
        follower_count=competitor.follower_count,
        is_market_leader=competitor.is_market_leader,
        market_position=competitor.market_position,
        discovery_method=competitor.discovery_method,
    )
    db.add(db_competitor)

    try:
        await db.commit()
        await db.refresh(db_competitor)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Competitor with this Page ID already exists",
        )

    return CompetitorResponse.model_validate(db_competitor)


@router.get("/{competitor_id}", response_model=CompetitorResponse)
async def get_competitor(
    db: DbSession,
    competitor_id: UUID,
) -> CompetitorResponse:
    """Get a competitor by ID."""
    result = await db.execute(
        select(Competitor).where(Competitor.id == competitor_id)
    )
    competitor = result.scalar_one_or_none()

    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )

    ad_count = (
        await db.execute(
            select(func.count()).where(Ad.competitor_id == competitor.id)
        )
    ).scalar() or 0

    response = CompetitorResponse.model_validate(competitor)
    response.ad_count = ad_count

    return response


@router.put("/{competitor_id}", response_model=CompetitorResponse)
async def update_competitor(
    db: DbSession,
    competitor_id: UUID,
    competitor_update: CompetitorUpdate,
) -> CompetitorResponse:
    """Update a competitor."""
    result = await db.execute(
        select(Competitor).where(Competitor.id == competitor_id)
    )
    db_competitor = result.scalar_one_or_none()

    if not db_competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )

    update_data = competitor_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_competitor, field, value)

    await db.commit()
    await db.refresh(db_competitor)

    return CompetitorResponse.model_validate(db_competitor)


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_competitor(
    db: DbSession,
    competitor_id: UUID,
) -> None:
    """Deactivate a competitor (soft delete)."""
    result = await db.execute(
        select(Competitor).where(Competitor.id == competitor_id)
    )
    db_competitor = result.scalar_one_or_none()

    if not db_competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )

    db_competitor.active = False
    await db.commit()


@router.post("/discover", response_model=CompetitorDiscoverResponse)
async def discover_competitors(
    db: DbSession,
    request: CompetitorDiscoverRequest,
) -> CompetitorDiscoverResponse:
    """
    Automatically discover competitors using AI.

    This endpoint uses AI to research and identify potential competitors
    based on the business strategy information.
    """
    from app.models.business_strategy import BusinessStrategy

    strategy_result = await db.execute(
        select(BusinessStrategy).order_by(BusinessStrategy.last_updated.desc()).limit(1)
    )
    strategy = strategy_result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No business strategy found. Please create a strategy first.",
        )

    try:
        discovery = CompetitorDiscovery()
        discovered = await discovery.discover_competitors(
            business_name=strategy.business_name,
            industry=request.industry or strategy.industry,
            business_description=strategy.business_description,
            max_competitors=request.max_competitors,
        )
    except CompetitorDiscoveryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Competitor discovery failed: {e}",
        )

    added_competitors = []
    already_tracked = 0
    pending_manual_review = []

    for comp_data in discovered:
        company_name = comp_data.get("company_name")

        # Search Facebook pages by company name using Google
        page_id = None
        facebook_url = None
        try:
            logger.info(f"Searching Google for Facebook page: {company_name}")
            page_id, facebook_url = await discovery.search_for_page_id(company_name)
        except Exception as e:
            logger.warning(f"Facebook page search failed for {company_name}: {e}")

        # If no page_id found, add to pending review list with URL if available
        if not page_id:
            pending_manual_review.append({
                "company_name": company_name,
                "relevance_reason": comp_data.get("reason"),
                "description": comp_data.get("description"),
            })
            continue

        existing = await db.execute(
            select(Competitor).where(Competitor.page_id == page_id)
        )
        if existing.scalar_one_or_none():
            already_tracked += 1
            continue

        db_competitor = Competitor(
            company_name=company_name,
            page_id=page_id,
            industry=strategy.industry,
            discovery_method="automated",
            metadata_={
                "relevance_reason": comp_data.get("reason"),
                "description": comp_data.get("description"),
            },
        )
        db.add(db_competitor)
        added_competitors.append(db_competitor)

    await db.commit()

    for comp in added_competitors:
        await db.refresh(comp)

    return CompetitorDiscoverResponse(
        discovered=[CompetitorResponse.model_validate(c) for c in added_competitors],
        total_found=len(discovered),
        already_tracked=already_tracked,
        pending_manual_review=pending_manual_review,
    )
