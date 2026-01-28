"""Onboarding API endpoints for brand profile creation."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.models.brand_profile import BrandProfile
from app.schemas.brand_profile import (
    INDUSTRY_OPTIONS,
    TONE_OPTIONS,
    BrandProfileListResponse,
    BrandProfileResponse,
    BrandProfileUpdate,
    OnboardingCompleteRequest,
    OnboardingStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_brand_profile_response(profile: BrandProfile) -> BrandProfileResponse:
    """Build a brand profile response from the model."""
    # Convert JSONB lists to proper Python lists
    competitors = None
    if profile.competitors and isinstance(profile.competitors, list):
        competitors = [UUID(str(c)) for c in profile.competitors]

    keywords = None
    if profile.keywords and isinstance(profile.keywords, list):
        keywords = list(profile.keywords)

    forbidden_terms = None
    if profile.forbidden_terms and isinstance(profile.forbidden_terms, list):
        forbidden_terms = list(profile.forbidden_terms)

    return BrandProfileResponse(
        id=profile.id,
        industry=profile.industry,
        niche=profile.niche,
        core_offer=profile.core_offer,
        competitors=competitors,
        keywords=keywords,
        tone=profile.tone,
        forbidden_terms=forbidden_terms,
        logo_url=profile.logo_url,
        primary_color=profile.primary_color,
        font_family=profile.font_family,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    db: DbSession,
) -> OnboardingStatusResponse:
    """
    Check onboarding status.

    Returns whether the user has completed onboarding and their brand profile if it exists.
    For MVP, we assume a single user/brand profile per installation.
    """
    # Get the most recent brand profile
    result = await db.execute(
        select(BrandProfile).order_by(BrandProfile.created_at.desc()).limit(1)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return OnboardingStatusResponse(
            has_brand_profile=False,
            brand_profile=None,
            completed_steps=0,
        )

    # Calculate completed steps based on filled fields
    completed_steps = 0
    if profile.industry:
        completed_steps = 1
    if profile.core_offer:
        completed_steps = 2
    if profile.competitors or completed_steps == 2:
        # Step 3 is considered complete even if no competitors selected
        completed_steps = 3

    return OnboardingStatusResponse(
        has_brand_profile=True,
        brand_profile=_build_brand_profile_response(profile),
        completed_steps=completed_steps,
    )


@router.post("", response_model=BrandProfileResponse, status_code=status.HTTP_201_CREATED)
async def complete_onboarding(
    db: DbSession,
    request: OnboardingCompleteRequest,
) -> BrandProfileResponse:
    """
    Complete the onboarding flow and create a brand profile.

    This endpoint creates a new brand profile with all the information
    gathered during the 3-step onboarding flow:
    1. Industry/Niche selection
    2. Core Offer description
    3. Competitors selection

    **Note:** For MVP, creating a new profile will be the primary brand profile.
    """
    # Convert competitors list to JSONB format
    competitors_json = None
    if request.competitors:
        competitors_json = [str(c) for c in request.competitors]

    # Create the brand profile
    db_profile = BrandProfile(
        industry=request.industry,
        niche=request.niche,
        core_offer=request.core_offer,
        competitors=competitors_json,
        keywords=request.keywords,
        tone=request.tone,
        forbidden_terms=request.forbidden_terms,
        logo_url=request.logo_url,
        primary_color=request.primary_color,
        font_family=request.font_family,
    )

    db.add(db_profile)
    await db.commit()
    await db.refresh(db_profile)

    logger.info(f"Created brand profile {db_profile.id} for industry: {request.industry}")

    return _build_brand_profile_response(db_profile)


@router.get("", response_model=BrandProfileResponse)
async def get_brand_profile(
    db: DbSession,
) -> BrandProfileResponse:
    """
    Get the current brand profile.

    For MVP, returns the most recently created brand profile.
    """
    result = await db.execute(
        select(BrandProfile).order_by(BrandProfile.created_at.desc()).limit(1)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No brand profile found. Please complete onboarding first.",
        )

    return _build_brand_profile_response(profile)


@router.get("/all", response_model=BrandProfileListResponse)
async def list_brand_profiles(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> BrandProfileListResponse:
    """List all brand profiles with pagination."""
    # Count total
    count_result = await db.execute(select(func.count()).select_from(BrandProfile))
    total = count_result.scalar() or 0

    # Get paginated results
    query = select(BrandProfile).order_by(BrandProfile.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    profiles = result.scalars().all()

    return BrandProfileListResponse(
        items=[_build_brand_profile_response(p) for p in profiles],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/options/industries")
async def get_industry_options() -> list[dict]:
    """Get available industry options for the onboarding form."""
    return INDUSTRY_OPTIONS


@router.get("/options/tones")
async def get_tone_options() -> list[dict]:
    """Get available tone options for the onboarding form."""
    return TONE_OPTIONS


@router.get("/{profile_id}", response_model=BrandProfileResponse)
async def get_brand_profile_by_id(
    db: DbSession,
    profile_id: UUID,
) -> BrandProfileResponse:
    """Get a specific brand profile by ID."""
    result = await db.execute(select(BrandProfile).where(BrandProfile.id == profile_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found",
        )

    return _build_brand_profile_response(profile)


@router.put("/{profile_id}", response_model=BrandProfileResponse)
async def update_brand_profile(
    db: DbSession,
    profile_id: UUID,
    request: BrandProfileUpdate,
) -> BrandProfileResponse:
    """Update an existing brand profile."""
    result = await db.execute(select(BrandProfile).where(BrandProfile.id == profile_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)

    # Convert competitors to JSONB format if provided
    if "competitors" in update_data and update_data["competitors"] is not None:
        update_data["competitors"] = [str(c) for c in update_data["competitors"]]

    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    logger.info(f"Updated brand profile {profile_id}")

    return _build_brand_profile_response(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand_profile(
    db: DbSession,
    profile_id: UUID,
) -> None:
    """Delete a brand profile."""
    result = await db.execute(select(BrandProfile).where(BrandProfile.id == profile_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found",
        )

    await db.delete(profile)
    await db.commit()

    logger.info(f"Deleted brand profile {profile_id}")
