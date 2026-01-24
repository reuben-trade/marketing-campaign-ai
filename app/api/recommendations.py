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
from app.services.video_analyzer import VideoAnalyzer, VideoAnalysisError
from app.services.semantic_search_service import SemanticSearchService

logger = logging.getLogger(__name__)
router = APIRouter()


def _normalize_stored_recommendations(recommendations: list[dict] | None) -> list[dict]:
    """
    Normalize recommendation data loaded from database to match Pydantic schema.

    This handles legacy data where the LLM returned simplified structures
    (e.g., strings instead of objects for copywriting fields).
    """
    if not recommendations:
        return []

    normalized = []
    for rec in recommendations:
        rec = dict(rec)  # Make a copy to avoid modifying the original

        # Normalize copywriting fields - convert strings to CopyElement objects
        if "copywriting" in rec and rec["copywriting"]:
            copywriting = dict(rec["copywriting"])
            for field in ["headline", "subheadline", "body_copy", "cta_button"]:
                if field in copywriting:
                    value = copywriting[field]
                    if isinstance(value, str):
                        copywriting[field] = {
                            "text": value,
                            "placement": "center" if field == "headline" else "below headline",
                        }
                    elif isinstance(value, dict):
                        if "text" not in value:
                            value["text"] = str(value.get("content", ""))
                        if "placement" not in value:
                            value["placement"] = "center" if field == "headline" else "below"
            rec["copywriting"] = copywriting

        # Normalize content_breakdown fields
        if "content_breakdown" in rec and rec["content_breakdown"]:
            content_breakdown = dict(rec["content_breakdown"])
            for field in ["left_side_problem", "right_side_solution"]:
                if field in content_breakdown:
                    value = content_breakdown[field]
                    if isinstance(value, str):
                        content_breakdown[field] = {
                            "visual": value,
                            "text": "",
                            "style": "bold",
                        }
                    elif isinstance(value, dict):
                        if "visual" not in value:
                            value["visual"] = str(value.get("description", ""))
                        if "text" not in value:
                            value["text"] = ""
                        if "style" not in value:
                            value["style"] = "bold"
            rec["content_breakdown"] = content_breakdown

        # Normalize visual_direction.color_palette
        if "visual_direction" in rec and rec["visual_direction"]:
            vd = dict(rec["visual_direction"])
            if "color_palette" in vd and vd["color_palette"]:
                cp = dict(vd["color_palette"])
                if "primary" not in cp:
                    cp["primary"] = cp.get("main", "#000000")
                if "secondary" not in cp:
                    cp["secondary"] = cp.get("accent", "#333333")
                if "accent" not in cp:
                    cp["accent"] = cp.get("highlight", "#666666")
                vd["color_palette"] = cp
            rec["visual_direction"] = vd

        # Normalize testing_variants
        if "testing_variants" in rec:
            if rec["testing_variants"] is None:
                rec["testing_variants"] = []
            elif not isinstance(rec["testing_variants"], list):
                rec["testing_variants"] = [rec["testing_variants"]]

        # Normalize success_metrics.secondary
        if "success_metrics" in rec and rec["success_metrics"]:
            sm = dict(rec["success_metrics"])
            if "secondary" in sm and not isinstance(sm["secondary"], list):
                if isinstance(sm["secondary"], str):
                    sm["secondary"] = [sm["secondary"]]
                elif sm["secondary"] is None:
                    sm["secondary"] = []
            rec["success_metrics"] = sm

        # Normalize production_notes.assets_needed
        if "production_notes" in rec and rec["production_notes"]:
            notes = dict(rec["production_notes"])
            if "assets_needed" in notes and not isinstance(notes["assets_needed"], list):
                if isinstance(notes["assets_needed"], str):
                    notes["assets_needed"] = [notes["assets_needed"]]
                elif notes["assets_needed"] is None:
                    notes["assets_needed"] = []
            rec["production_notes"] = notes

        # Normalize design_specifications.colors
        if "design_specifications" in rec and rec["design_specifications"]:
            specs = dict(rec["design_specifications"])
            if "colors" in specs and not isinstance(specs["colors"], dict):
                if isinstance(specs["colors"], list):
                    specs["colors"] = {f"color_{i}": c for i, c in enumerate(specs["colors"])}
                elif isinstance(specs["colors"], str):
                    specs["colors"] = {"primary": specs["colors"]}
            rec["design_specifications"] = specs

        normalized.append(rec)

    return normalized


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

    Optionally analyzes user's own ad for comparison if user_ad_id is provided.
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

    # Fetch competitor ads with optional semantic relevance filtering
    if request.relevance_description:
        # Use semantic search to filter relevant ads
        search_service = SemanticSearchService()
        relevant_ads = await search_service.filter_relevant_ads(
            db=db,
            intent_description=request.relevance_description,
            intent_themes=request.relevance_themes or [],
            min_similarity=request.min_similarity,
        )

        # Apply additional filters and sorting
        ads = []
        for ad in relevant_ads:
            # Check date range filters
            if request.date_range_start and ad.publication_date < request.date_range_start:
                continue
            if request.date_range_end and ad.publication_date > request.date_range_end:
                continue
            ads.append(ad)

        # Sort by engagement and limit
        ads.sort(key=lambda ad: ad.total_engagement, reverse=True)
        ads = ads[:request.top_n_ads]

    else:
        # Traditional filtering by engagement
        ads_query = (
            select(Ad)
            .options(
                selectinload(Ad.competitor),
                selectinload(Ad.elements),
                selectinload(Ad.creative_analysis),
            )
            .where(
                and_(
                    Ad.analyzed == True,  # noqa: E712
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

    # Build ads list with rich video_intelligence data
    ads_list = []
    for ad in ads:
        ad_data = {
            "id": str(ad.id),
            "competitor_name": ad.competitor.company_name if ad.competitor else "Unknown",
            "creative_type": ad.creative_type,
            "likes": ad.likes or 0,
            "comments": ad.comments or 0,
            "shares": ad.shares or 0,
            "analysis": ad.analysis,
            "video_intelligence": ad.video_intelligence,
        }

        # Include ad elements (narrative beats)
        if ad.elements:
            ad_data["elements"] = [
                {
                    "beat_type": elem.beat_type,
                    "start_time": elem.start_time,
                    "end_time": elem.end_time,
                    "visual_description": elem.visual_description,
                    "audio_transcript": elem.audio_transcript,
                    "tone_of_voice": elem.tone_of_voice,
                    "emotion": elem.emotion,
                    "emotion_intensity": elem.emotion_intensity,
                    "camera_angle": elem.camera_angle,
                    "lighting_style": elem.lighting_style,
                    "color_grading": elem.color_grading,
                    "motion_type": elem.motion_type,
                    "text_overlays": elem.text_overlays,
                    "rhetorical_mode": elem.rhetorical_mode,
                    "persuasion_techniques": elem.persuasion_techniques,
                }
                for elem in ad.elements
            ]

        # Include creative analysis metrics
        if ad.creative_analysis:
            ca = ad.creative_analysis
            ad_data["creative_analysis"] = {
                "hook_score": ca.hook_score,
                "copy_framework": ca.copy_framework,
                "headline_text": ca.headline_text,
                "cta_text": ca.cta_text,
                "production_style": ca.production_style,
                "production_quality_score": ca.production_quality_score,
                "thumb_stop_score": ca.thumb_stop_score,
                "overall_grade": ca.overall_grade,
            }

        ads_list.append(ad_data)

    # Handle user's own ad analysis if provided
    user_ad_analysis = None
    if request.user_ad_id:
        user_ad_result = await db.execute(
            select(Ad)
            .options(
                selectinload(Ad.elements),
                selectinload(Ad.creative_analysis),
            )
            .where(Ad.id == request.user_ad_id)
        )
        user_ad = user_ad_result.scalar_one_or_none()

        if not user_ad:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User ad with ID {request.user_ad_id} not found.",
            )

        # If user's ad hasn't been analyzed with V2, analyze it now
        if not user_ad.video_intelligence and user_ad.creative_storage_path:
            try:
                video_analyzer = VideoAnalyzer()
                analysis_result = await video_analyzer.analyze_from_storage_v2(
                    storage_path=user_ad.creative_storage_path,
                    competitor_name=strategy.business_name or "User",
                    market_position=strategy.market_position,
                    brand_name=strategy.business_name,
                    industry=strategy.industry,
                    target_audience=str(strategy.target_audience) if strategy.target_audience else None,
                    likes=user_ad.likes or 0,
                    comments=user_ad.comments or 0,
                    shares=user_ad.shares or 0,
                    platform_cta=user_ad.cta_text,
                )

                # Store the analysis
                user_ad.video_intelligence = analysis_result
                user_ad.analyzed = True
                user_ad.analysis_status = "completed"
                await db.commit()
                await db.refresh(user_ad)

                logger.info(f"Analyzed user ad {user_ad.id} with Gemini V2")
            except VideoAnalysisError as e:
                logger.warning(f"Failed to analyze user ad: {e}")
                # Continue without user ad analysis

        # Build user ad data structure
        user_ad_analysis = {
            "id": str(user_ad.id),
            "creative_type": user_ad.creative_type,
            "likes": user_ad.likes or 0,
            "comments": user_ad.comments or 0,
            "shares": user_ad.shares or 0,
            "analysis": user_ad.analysis,
            "video_intelligence": user_ad.video_intelligence,
        }

        if user_ad.elements:
            user_ad_analysis["elements"] = [
                {
                    "beat_type": elem.beat_type,
                    "start_time": elem.start_time,
                    "end_time": elem.end_time,
                    "visual_description": elem.visual_description,
                    "audio_transcript": elem.audio_transcript,
                    "tone_of_voice": elem.tone_of_voice,
                    "emotion": elem.emotion,
                    "emotion_intensity": elem.emotion_intensity,
                    "camera_angle": elem.camera_angle,
                    "lighting_style": elem.lighting_style,
                    "color_grading": elem.color_grading,
                    "motion_type": elem.motion_type,
                    "text_overlays": elem.text_overlays,
                    "rhetorical_mode": elem.rhetorical_mode,
                    "persuasion_techniques": elem.persuasion_techniques,
                }
                for elem in user_ad.elements
            ]

        if user_ad.creative_analysis:
            ca = user_ad.creative_analysis
            user_ad_analysis["creative_analysis"] = {
                "hook_score": ca.hook_score,
                "copy_framework": ca.copy_framework,
                "headline_text": ca.headline_text,
                "cta_text": ca.cta_text,
                "production_style": ca.production_style,
                "production_quality_score": ca.production_quality_score,
                "thumb_stop_score": ca.thumb_stop_score,
                "overall_grade": ca.overall_grade,
            }

    try:
        engine = RecommendationEngine()
        recommendations, generation_time, model_used = await engine.generate_recommendations(
            business_strategy=strategy_dict,
            analyzed_ads=ads_list,
            model=model,
            num_video_ideas=request.num_video_ideas,
            num_image_ideas=request.num_image_ideas,
            user_ad_analysis=user_ad_analysis,
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
        ads_analyzed=[str(ad.id) for ad in ads],
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
        recommendations=_normalize_stored_recommendations(recommendation.recommendations),
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
        recommendations=_normalize_stored_recommendations(recommendation.recommendations),
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
                recommendations=_normalize_stored_recommendations(rec.recommendations),
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
