"""Ad analysis background tasks."""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_sync_session():
    """Get a synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config import get_settings

    settings = get_settings()
    sync_url = settings.database_url.replace("+asyncpg", "")

    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(bind=True, max_retries=3)
def analyze_pending_ads_task(self, batch_size: int = 50):
    """
    Analyze all pending ads.

    This task runs daily to analyze newly downloaded ads.
    """
    from app.models.ad import Ad
    from app.models.analysis_run import AnalysisRun

    session = get_sync_session()

    run = AnalysisRun(
        run_type="ad_analysis",
        status="running",
        parameters={"batch_size": batch_size},
    )
    session.add(run)
    session.commit()

    try:
        pending_ads = (
            session.query(Ad)
            .filter(
                Ad.analyzed.is_(False),
                Ad.download_status == "completed",
                Ad.analysis_status == "pending",
            )
            .limit(batch_size)
            .all()
        )

        processed = 0
        failed = 0

        for ad in pending_ads:
            result = analyze_single_ad_task.delay(str(ad.id))

            try:
                task_result = result.get(timeout=120)
                if task_result.get("status") == "completed":
                    processed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to analyze ad {ad.id}: {e}")
                failed += 1

        run.status = "completed"
        run.items_processed = processed
        run.items_failed = failed
        run.completed_at = datetime.utcnow()
        run.logs = {
            "batch_size": batch_size,
            "total_pending": len(pending_ads),
            "processed": processed,
            "failed": failed,
        }
        session.commit()

        logger.info(f"Ad analysis completed: {processed} processed, {failed} failed")

        return {
            "status": "completed",
            "processed": processed,
            "failed": failed,
            "total": len(pending_ads),
        }

    except Exception as e:
        logger.error(f"Ad analysis batch failed: {e}")
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()
        session.commit()

        self.retry(exc=e, countdown=60 * 5)

    finally:
        session.close()


@celery_app.task(bind=True, max_retries=2)
def analyze_single_ad_task(self, ad_id: str):
    """
    Analyze a single ad.

    This task can be triggered manually or by the batch analysis task.
    """
    from app.models.ad import Ad
    from app.models.competitor import Competitor
    from app.services.image_analyzer import ImageAnalysisError, ImageAnalyzer
    from app.services.video_analyzer import VideoAnalysisError, VideoAnalyzer

    session = get_sync_session()

    try:
        ad = session.query(Ad).filter(Ad.id == UUID(ad_id)).first()

        if not ad:
            return {"error": "Ad not found"}

        if ad.download_status != "completed":
            return {"error": "Ad creative not downloaded"}

        competitor = session.query(Competitor).filter(Competitor.id == ad.competitor_id).first()

        if not competitor:
            return {"error": "Competitor not found"}

        try:
            if ad.creative_type == "image":
                analyzer = ImageAnalyzer()
                analysis = asyncio.run(
                    analyzer.analyze_from_storage(
                        ad.creative_storage_path,
                        competitor_name=competitor.company_name,
                        market_position=competitor.market_position,
                        follower_count=competitor.follower_count,
                        likes=ad.likes,
                        comments=ad.comments,
                        shares=ad.shares,
                    )
                )
            else:
                analyzer = VideoAnalyzer()
                analysis = asyncio.run(
                    analyzer.analyze_from_storage(
                        ad.creative_storage_path,
                        competitor_name=competitor.company_name,
                        market_position=competitor.market_position,
                        follower_count=competitor.follower_count,
                        likes=ad.likes,
                        comments=ad.comments,
                        shares=ad.shares,
                    )
                )

            ad.analysis = analysis
            ad.analyzed = True
            ad.analyzed_date = datetime.utcnow()
            ad.analysis_status = "completed"
            session.commit()

            logger.info(f"Analyzed ad {ad_id}")

            # Trigger scoring and embedding tasks
            from app.tasks.scoring_tasks import calculate_composite_score_task, embed_ad_task

            # These run asynchronously after analysis completes
            calculate_composite_score_task.delay(ad_id)
            embed_ad_task.delay(ad_id)

            return {
                "status": "completed",
                "ad_id": ad_id,
                "creative_type": ad.creative_type,
                "overall_score": analysis.get("marketing_effectiveness", {}).get("overall_score"),
            }

        except (ImageAnalysisError, VideoAnalysisError) as e:
            logger.error(f"Analysis failed for ad {ad_id}: {e}")
            ad.analysis_status = "failed"
            session.commit()

            self.retry(exc=e, countdown=60 * 2)

    except Exception as e:
        logger.error(f"Failed to analyze ad {ad_id}: {e}")
        return {"error": str(e)}

    finally:
        session.close()


@celery_app.task
def reanalyze_failed_ads_task():
    """
    Retry analysis for ads that previously failed.

    This task can be triggered manually to retry failed analyses.
    """
    from app.models.ad import Ad

    session = get_sync_session()

    try:
        failed_ads = (
            session.query(Ad)
            .filter(
                Ad.download_status == "completed",
                Ad.analysis_status == "failed",
            )
            .all()
        )

        queued = 0
        for ad in failed_ads:
            ad.analysis_status = "pending"
            analyze_single_ad_task.delay(str(ad.id))
            queued += 1

        session.commit()

        logger.info(f"Queued {queued} failed ads for reanalysis")

        return {
            "status": "completed",
            "queued": queued,
        }

    except Exception as e:
        logger.error(f"Failed to queue reanalysis: {e}")
        return {"error": str(e)}

    finally:
        session.close()
