"""Celery tasks for composite scoring and embedding generation."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models.ad import Ad
from app.services.composite_scoring_service import CompositeScoreCalculator
from app.services.embedding_service import EmbeddingService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="calculate_composite_score")
def calculate_composite_score_task(ad_id: str) -> dict[str, any]:
    """
    Calculate composite score for a single ad.

    Triggered after ad analysis completes.

    Args:
        ad_id: UUID of ad to score (as string)

    Returns:
        dict with success status and score
    """
    import asyncio

    async def _calculate():
        async with async_session() as db:
            try:
                # Get ad with related data
                result = await db.execute(
                    select(Ad)
                    .options(
                        selectinload(Ad.competitor),
                        selectinload(Ad.creative_analysis),
                    )
                    .where(Ad.id == UUID(ad_id))
                )
                ad = result.scalar_one_or_none()

                if not ad:
                    logger.error(f"Ad {ad_id} not found")
                    return {"success": False, "error": "Ad not found"}

                # Calculate score
                score_calculator = CompositeScoreCalculator()
                composite_score = await score_calculator.calculate_composite_score(db, ad)

                await db.commit()

                logger.info(f"Calculated composite score for ad {ad_id}: {composite_score:.3f}")

                return {
                    "success": True,
                    "ad_id": str(ad.id),
                    "composite_score": composite_score,
                }

            except Exception as e:
                logger.error(f"Failed to calculate score for ad {ad_id}: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}

    return asyncio.run(_calculate())


@celery_app.task(name="embed_ad")
def embed_ad_task(ad_id: str) -> dict[str, any]:
    """
    Generate embedding for a single ad.

    Triggered after ad analysis completes.

    Args:
        ad_id: UUID of ad to embed (as string)

    Returns:
        dict with success status
    """
    import asyncio

    async def _embed():
        async with async_session() as db:
            try:
                # Get ad
                result = await db.execute(select(Ad).where(Ad.id == UUID(ad_id)))
                ad = result.scalar_one_or_none()

                if not ad:
                    logger.error(f"Ad {ad_id} not found")
                    return {"success": False, "error": "Ad not found"}

                # Generate embedding
                embedding_service = EmbeddingService()
                await embedding_service.embed_ad(db, ad)

                await db.commit()

                logger.info(f"Generated embedding for ad {ad_id}")

                return {
                    "success": True,
                    "ad_id": str(ad.id),
                }

            except Exception as e:
                logger.error(f"Failed to embed ad {ad_id}: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}

    return asyncio.run(_embed())


@celery_app.task(name="calculate_composite_scores_batch")
def calculate_composite_scores_batch_task(limit: int = 100) -> dict[str, int]:
    """
    Calculate composite scores for multiple ads without scores.

    Args:
        limit: Maximum number of ads to process

    Returns:
        dict with processed and failed counts
    """
    import asyncio

    async def _calculate_batch():
        async with async_session() as db:
            try:
                score_calculator = CompositeScoreCalculator()

                # Get ads that need scoring
                result = await db.execute(
                    select(Ad)
                    .options(
                        selectinload(Ad.competitor),
                        selectinload(Ad.creative_analysis),
                    )
                    .where(
                        Ad.analyzed == True,  # noqa: E712
                        Ad.analysis_status == "completed",
                        Ad.composite_score.is_(None),
                    )
                    .limit(limit)
                )
                ads = result.scalars().all()

                if not ads:
                    logger.info("No ads need scoring")
                    return {"processed": 0, "failed": 0}

                processed = 0
                failed = 0

                for ad in ads:
                    try:
                        await score_calculator.calculate_composite_score(db, ad)
                        processed += 1

                        # Commit in batches of 10
                        if processed % 10 == 0:
                            await db.commit()

                    except Exception as e:
                        logger.error(f"Failed to calculate score for ad {ad.id}: {e}")
                        failed += 1

                # Final commit
                await db.commit()

                logger.info(f"Batch scoring: {processed} processed, {failed} failed")

                return {"processed": processed, "failed": failed}

            except Exception as e:
                logger.error(f"Batch scoring failed: {e}")
                await db.rollback()
                return {"processed": 0, "failed": 0}

    return asyncio.run(_calculate_batch())


@celery_app.task(name="embed_ads_batch")
def embed_ads_batch_task(limit: int = 100) -> dict[str, int]:
    """
    Generate embeddings for multiple ads without embeddings.

    Args:
        limit: Maximum number of ads to process

    Returns:
        dict with processed and failed counts
    """
    import asyncio

    async def _embed_batch():
        async with async_session() as db:
            try:
                embedding_service = EmbeddingService()

                result = await embedding_service.embed_batch(db=db, limit=limit)

                logger.info(
                    f"Batch embedding: {result['processed']} processed, {result['failed']} failed"
                )

                return result

            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                return {"processed": 0, "failed": 0}

    return asyncio.run(_embed_batch())


@celery_app.task(name="recalculate_percentiles")
def recalculate_percentiles_task() -> dict[str, int]:
    """
    Recalculate engagement percentiles for all ads.

    Runs daily via Celery Beat to update percentiles as new ads are added.

    Returns:
        dict with processed and skipped counts
    """
    import asyncio

    async def _recalculate():
        async with async_session() as db:
            try:
                score_calculator = CompositeScoreCalculator()

                result = await score_calculator.recalculate_all_percentiles(db)

                logger.info(
                    f"Recalculated percentiles: {result['processed']} processed, "
                    f"{result['skipped']} skipped"
                )

                return result

            except Exception as e:
                logger.error(f"Percentile recalculation failed: {e}")
                return {"processed": 0, "skipped": 0}

    return asyncio.run(_recalculate())
