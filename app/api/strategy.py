"""Strategy API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession
from app.models.business_strategy import BusinessStrategy
from app.schemas.business_strategy import (
    BusinessStrategyCreate,
    BusinessStrategyExtractResponse,
    BusinessStrategyResponse,
    BusinessStrategyUpdate,
)
from app.services.strategy_extractor import StrategyExtractionError, StrategyExtractor
from app.utils.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=BusinessStrategyExtractResponse)
async def upload_and_extract_strategy(
    db: DbSession,
    file: UploadFile = File(...),
) -> BusinessStrategyExtractResponse:
    """
    Upload a PDF strategy document and extract structured data.

    The PDF will be stored in Supabase Storage and analyzed using AI
    to extract business strategy information.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF",
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 10MB",
        )

    try:
        extractor = StrategyExtractor()
        strategy_data, confidence, missing_fields = await extractor.extract_from_pdf(content)
    except StrategyExtractionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract strategy from PDF: {e}",
        )

    db_strategy = BusinessStrategy(
        business_name=strategy_data.business_name,
        business_description=strategy_data.business_description,
        industry=strategy_data.industry,
        target_audience=strategy_data.target_audience.model_dump() if strategy_data.target_audience else None,
        brand_voice=strategy_data.brand_voice.model_dump() if strategy_data.brand_voice else None,
        market_position=strategy_data.market_position,
        price_point=strategy_data.price_point,
        business_life_stage=strategy_data.business_life_stage,
        unique_selling_points=strategy_data.unique_selling_points,
        competitive_advantages=strategy_data.competitive_advantages,
        marketing_objectives=strategy_data.marketing_objectives,
    )
    db.add(db_strategy)
    await db.flush()

    storage = SupabaseStorage()
    try:
        storage_path = await storage.upload_strategy_document(
            db_strategy.id,
            content,
            file.filename,
        )
        db_strategy.raw_pdf_url = storage.get_public_url(
            storage_path,
            bucket=storage.strategy_documents_bucket,
        )
    except Exception as e:
        logger.warning(f"Failed to upload PDF to storage: {e}")

    await db.commit()
    await db.refresh(db_strategy)

    return BusinessStrategyExtractResponse(
        strategy=BusinessStrategyResponse.model_validate(db_strategy),
        extraction_confidence=confidence,
        missing_fields=missing_fields,
    )


@router.post("", response_model=BusinessStrategyResponse)
async def create_strategy(
    db: DbSession,
    strategy: BusinessStrategyCreate,
) -> BusinessStrategyResponse:
    """Create a new business strategy manually."""
    db_strategy = BusinessStrategy(
        business_name=strategy.business_name,
        business_description=strategy.business_description,
        industry=strategy.industry,
        target_audience=strategy.target_audience.model_dump() if strategy.target_audience else None,
        brand_voice=strategy.brand_voice.model_dump() if strategy.brand_voice else None,
        market_position=strategy.market_position,
        price_point=strategy.price_point,
        business_life_stage=strategy.business_life_stage,
        unique_selling_points=strategy.unique_selling_points,
        competitive_advantages=strategy.competitive_advantages,
        marketing_objectives=strategy.marketing_objectives,
    )
    db.add(db_strategy)
    await db.commit()
    await db.refresh(db_strategy)

    return BusinessStrategyResponse.model_validate(db_strategy)


@router.get("/{strategy_id}", response_model=BusinessStrategyResponse)
async def get_strategy(
    db: DbSession,
    strategy_id: UUID,
) -> BusinessStrategyResponse:
    """Get a business strategy by ID."""
    result = await db.execute(
        select(BusinessStrategy).where(BusinessStrategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    return BusinessStrategyResponse.model_validate(strategy)


@router.put("/{strategy_id}", response_model=BusinessStrategyResponse)
async def update_strategy(
    db: DbSession,
    strategy_id: UUID,
    strategy_update: BusinessStrategyUpdate,
) -> BusinessStrategyResponse:
    """Update a business strategy."""
    result = await db.execute(
        select(BusinessStrategy).where(BusinessStrategy.id == strategy_id)
    )
    db_strategy = result.scalar_one_or_none()

    if not db_strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    update_data = strategy_update.model_dump(exclude_unset=True)

    if "target_audience" in update_data and update_data["target_audience"]:
        update_data["target_audience"] = update_data["target_audience"].model_dump()
    if "brand_voice" in update_data and update_data["brand_voice"]:
        update_data["brand_voice"] = update_data["brand_voice"].model_dump()

    for field, value in update_data.items():
        setattr(db_strategy, field, value)

    await db.commit()
    await db.refresh(db_strategy)

    return BusinessStrategyResponse.model_validate(db_strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    db: DbSession,
    strategy_id: UUID,
) -> None:
    """Delete a business strategy."""
    result = await db.execute(
        select(BusinessStrategy).where(BusinessStrategy.id == strategy_id)
    )
    db_strategy = result.scalar_one_or_none()

    if not db_strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    if db_strategy.raw_pdf_url:
        try:
            storage = SupabaseStorage()
            storage_path = f"{strategy_id}.pdf"
            await storage.delete_file(storage_path, bucket=storage.strategy_documents_bucket)
        except Exception as e:
            logger.warning(f"Failed to delete PDF from storage: {e}")

    await db.delete(db_strategy)
    await db.commit()


@router.get("", response_model=list[BusinessStrategyResponse])
async def list_strategies(
    db: DbSession,
) -> list[BusinessStrategyResponse]:
    """List all business strategies."""
    result = await db.execute(
        select(BusinessStrategy).order_by(BusinessStrategy.last_updated.desc())
    )
    strategies = result.scalars().all()

    return [BusinessStrategyResponse.model_validate(s) for s in strategies]
