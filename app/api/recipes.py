"""Recipe API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.recipe import (
    BeatDefinition,
    RecipeExtractRequest,
    RecipeExtractResponse,
    RecipeListResponse,
    RecipeResponse,
)
from app.services.recipe_extractor import RecipeExtractionError, RecipeExtractor

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=RecipeListResponse)
async def list_recipes(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    style: Annotated[str | None, Query(description="Filter by style: ugc, polished, etc.")] = None,
    pacing: Annotated[
        str | None, Query(description="Filter by pacing: fast, medium, slow, dynamic")
    ] = None,
    min_score: Annotated[
        float | None, Query(ge=0, le=1, description="Minimum composite score (0-1)")
    ] = None,
) -> RecipeListResponse:
    """
    List available recipes with optional filtering.

    Returns recipes sorted by composite score (highest first).
    """
    extractor = RecipeExtractor()
    recipes, total = await extractor.list_recipes(
        db,
        limit=limit,
        offset=offset,
        style=style,
        pacing=pacing,
        min_score=min_score,
    )

    return RecipeListResponse(
        recipes=[
            RecipeResponse(
                id=r.id,
                source_ad_id=r.source_ad_id,
                name=r.name,
                total_duration_seconds=r.total_duration_seconds,
                structure=[BeatDefinition(**b) for b in r.structure],
                pacing=r.pacing,
                style=r.style,
                composite_score=r.composite_score,
                created_at=r.created_at,
            )
            for r in recipes
        ],
        total=total,
    )


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecipeResponse:
    """Get recipe details by ID."""
    extractor = RecipeExtractor()
    recipe = await extractor.get_recipe(db, recipe_id)

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return RecipeResponse(
        id=recipe.id,
        source_ad_id=recipe.source_ad_id,
        name=recipe.name,
        total_duration_seconds=recipe.total_duration_seconds,
        structure=[BeatDefinition(**b) for b in recipe.structure],
        pacing=recipe.pacing,
        style=recipe.style,
        composite_score=recipe.composite_score,
        created_at=recipe.created_at,
    )


@router.post("/extract", response_model=RecipeExtractResponse)
async def extract_recipe(
    request: RecipeExtractRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecipeExtractResponse:
    """
    Extract a structural recipe from an analyzed ad.

    The ad must have been analyzed (video_intelligence or elements populated).
    Returns the created recipe along with extraction notes.
    """
    extractor = RecipeExtractor()
    try:
        return await extractor.extract_from_ad(
            db,
            ad_id=request.ad_id,
            custom_name=request.name,
        )
    except RecipeExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a recipe by ID."""
    extractor = RecipeExtractor()
    deleted = await extractor.delete_recipe(db, recipe_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Recipe not found")
