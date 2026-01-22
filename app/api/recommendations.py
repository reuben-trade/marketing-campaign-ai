"""Recommendations API endpoints."""

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.models.ad import Ad
from app.models.business_strategy import BusinessStrategy
from app.models.recommendation import Recommendation
from app.schemas.recommendation import (
    RecommendationCreate,
    RecommendationListResponse,
    RecommendationResponse,
)
from app.services.recommendation_engine import RecommendationEngine, RecommendationError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=RecommendationResponse)
async def generate_recommendations(
    db: DbSession,
    request: RecommendationCreate,
    model: str | None = Query(None, description="Model to use: 'claude' or 'openai'"),
) -> RecommendationResponse:
    """
    Generate content recommendations based on competitor analysis.

    Uses the business strategy and top-performing competitor ads
    to generate detailed, actionable content recommendations.
    """
    strategy_result = await db.execute(
        select(BusinessStrategy).order_by(BusinessStrategy.last_updated.desc()).limit(1)
    )
    strategy = strategy_result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No business strategy found. Please create a strategy first.",
        )

    ads_query = (
        select(Ad)
        .options(selectinload(Ad.competitor))
        .where(
            and_(
                Ad.analyzed == True,
                Ad.analysis_status == "completed",
            )
        )
    )

    if request.date_range_start:
        ads_query = ads_query.where(Ad.publication_date >= request.date_range_start)
    if request.date_range_end:
        ads_query = ads_query.where(Ad.publication_date <= request.date_range_end)

    ads_query = ads_query.order_by(
        (Ad.likes + Ad.comments + Ad.shares).desc()
    ).limit(request.top_n_ads)

    result = await db.execute(ads_query)
    ads = result.scalars().all()

    if not ads:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No analyzed ads found. Please retrieve and analyze competitor ads first.",
        )

    strategy_dict = {
        "business_name": strategy.business_name,
        "business_description": strategy.business_description,
        "industry": strategy.industry,
        "target_audience": strategy.target_audience,
        "brand_voice": strategy.brand_voice,
        "market_position": strategy.market_position,
        "price_point": strategy.price_point,
        "business_life_stage": strategy.business_life_stage,
        "unique_selling_points": strategy.unique_selling_points,
        "competitive_advantages": strategy.competitive_advantages,
        "marketing_objectives": strategy.marketing_objectives,
    }

    ads_list = []
    for ad in ads:
        ads_list.append({
            "id": str(ad.id),
            "competitor_name": ad.competitor.company_name,
            "creative_type": ad.creative_type,
            "likes": ad.likes,
            "comments": ad.comments,
            "shares": ad.shares,
            "analysis": ad.analysis,
        })

    try:
        engine = RecommendationEngine()
        recommendations, generation_time, model_used = await engine.generate_recommendations(
            business_strategy=strategy_dict,
            analyzed_ads=ads_list,
            model=model,
        )
    except RecommendationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {e}",
        )

    validation_errors = engine.validate_recommendations(recommendations)
    if validation_errors:
        logger.warning(f"Recommendation validation warnings: {validation_errors}")

    db_recommendation = Recommendation(
        top_n_ads=request.top_n_ads,
        date_range_start=request.date_range_start,
        date_range_end=request.date_range_end,
        trend_analysis=recommendations.get("trend_analysis"),
        recommendations=recommendations.get("recommendations"),
        executive_summary=recommendations.get("executive_summary"),
        implementation_roadmap=recommendations.get("implementation_roadmap"),
        ads_analyzed=[ad.id for ad in ads],
        generation_time_seconds=Decimal(str(round(generation_time, 2))),
        model_used=model_used,
    )
    db.add(db_recommendation)
    await db.commit()
    await db.refresh(db_recommendation)

    return RecommendationResponse(
        id=db_recommendation.id,
        generated_date=db_recommendation.generated_date,
        executive_summary=db_recommendation.executive_summary,
        trend_analysis=db_recommendation.trend_analysis,
        recommendations=db_recommendation.recommendations or [],
        implementation_roadmap=db_recommendation.implementation_roadmap,
        ads_analyzed=db_recommendation.ads_analyzed or [],
        generation_time_seconds=db_recommendation.generation_time_seconds,
        model_used=db_recommendation.model_used,
    )


@router.get("/latest", response_model=RecommendationResponse)
async def get_latest_recommendation(
    db: DbSession,
) -> RecommendationResponse:
    """Get the most recent recommendation."""
    result = await db.execute(
        select(Recommendation).order_by(Recommendation.generated_date.desc()).limit(1)
    )
    recommendation = result.scalar_one_or_none()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recommendations found",
        )

    return RecommendationResponse(
        id=recommendation.id,
        generated_date=recommendation.generated_date,
        executive_summary=recommendation.executive_summary,
        trend_analysis=recommendation.trend_analysis,
        recommendations=recommendation.recommendations or [],
        implementation_roadmap=recommendation.implementation_roadmap,
        ads_analyzed=recommendation.ads_analyzed or [],
        generation_time_seconds=recommendation.generation_time_seconds,
        model_used=recommendation.model_used,
    )


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    db: DbSession,
    recommendation_id: UUID,
) -> RecommendationResponse:
    """Get a recommendation by ID."""
    result = await db.execute(
        select(Recommendation).where(Recommendation.id == recommendation_id)
    )
    recommendation = result.scalar_one_or_none()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )

    return RecommendationResponse(
        id=recommendation.id,
        generated_date=recommendation.generated_date,
        executive_summary=recommendation.executive_summary,
        trend_analysis=recommendation.trend_analysis,
        recommendations=recommendation.recommendations or [],
        implementation_roadmap=recommendation.implementation_roadmap,
        ads_analyzed=recommendation.ads_analyzed or [],
        generation_time_seconds=recommendation.generation_time_seconds,
        model_used=recommendation.model_used,
    )


@router.get("", response_model=RecommendationListResponse)
async def list_recommendations(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
) -> RecommendationListResponse:
    """List all recommendations with pagination."""
    count_query = select(func.count()).select_from(Recommendation)
    total = (await db.execute(count_query)).scalar() or 0

    query = (
        select(Recommendation)
        .order_by(Recommendation.generated_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    recommendations = result.scalars().all()

    items = []
    for rec in recommendations:
        items.append(
            RecommendationResponse(
                id=rec.id,
                generated_date=rec.generated_date,
                executive_summary=rec.executive_summary,
                trend_analysis=rec.trend_analysis,
                recommendations=rec.recommendations or [],
                implementation_roadmap=rec.implementation_roadmap,
                ads_analyzed=rec.ads_analyzed or [],
                generation_time_seconds=rec.generation_time_seconds,
                model_used=rec.model_used,
            )
        )

    return RecommendationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{recommendation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recommendation(
    db: DbSession,
    recommendation_id: UUID,
) -> None:
    """Delete a recommendation."""
    result = await db.execute(
        select(Recommendation).where(Recommendation.id == recommendation_id)
    )
    recommendation = result.scalar_one_or_none()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )

    await db.delete(recommendation)
    await db.commit()
