"""Ad retrieval background tasks."""

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
def retrieve_all_ads_task(self, max_ads_per_competitor: int | None = None):
    """
    Retrieve ads for all active competitors.

    This task runs weekly to fetch new ads from all tracked competitors.
    """
    from app.config import get_settings
    from app.models.analysis_run import AnalysisRun
    from app.models.competitor import Competitor

    settings = get_settings()
    max_ads = max_ads_per_competitor or settings.max_ads_per_competitor

    session = get_sync_session()

    run = AnalysisRun(
        run_type="ad_retrieval",
        status="running",
        parameters={"max_ads_per_competitor": max_ads},
    )
    session.add(run)
    session.commit()

    try:
        competitors = (
            session.query(Competitor)
            .filter(Competitor.active == True)
            .all()
        )

        total_retrieved = 0
        total_failed = 0

        for competitor in competitors:
            result = retrieve_ads_for_competitor_task.delay(
                str(competitor.id),
                max_ads,
            )

            try:
                task_result = result.get(timeout=300)
                total_retrieved += task_result.get("retrieved", 0)
                total_failed += task_result.get("failed", 0)
            except Exception as e:
                logger.error(f"Failed to retrieve ads for competitor {competitor.id}: {e}")
                total_failed += 1

        run.status = "completed"
        run.items_processed = total_retrieved
        run.items_failed = total_failed
        run.completed_at = datetime.utcnow()
        run.logs = {
            "competitors_processed": len(competitors),
            "total_retrieved": total_retrieved,
            "total_failed": total_failed,
        }
        session.commit()

        logger.info(
            f"Ad retrieval completed: {total_retrieved} retrieved, {total_failed} failed"
        )

        return {
            "status": "completed",
            "competitors": len(competitors),
            "retrieved": total_retrieved,
            "failed": total_failed,
        }

    except Exception as e:
        logger.error(f"Ad retrieval failed: {e}")
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()
        session.commit()

        self.retry(exc=e, countdown=60 * 10)

    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3)
def retrieve_ads_for_competitor_task(
    self,
    competitor_id: str,
    max_ads: int = 100,
):
    """
    Retrieve ads for a single competitor.

    This task can be triggered manually or by the weekly batch task.
    """
    from app.models.ad import Ad
    from app.models.competitor import Competitor
    from app.services.ad_library_scraper import AdLibraryScraper, AdLibraryScraperError
    from app.services.creative_downloader import CreativeDownloader, CreativeDownloadError

    session = get_sync_session()

    try:
        competitor = (
            session.query(Competitor)
            .filter(Competitor.id == UUID(competitor_id))
            .first()
        )

        if not competitor:
            return {"error": "Competitor not found"}

        scraper = AdLibraryScraper()
        downloader = CreativeDownloader()

        try:
            scraped_ads = asyncio.run(
                scraper.scrape_ads_for_page(
                    competitor.page_id,
                    max_ads=max_ads,
                )
            )
        except AdLibraryScraperError as e:
            logger.error(f"Failed to scrape ads for {competitor_id}: {e}")
            self.retry(exc=e, countdown=60 * 5)
            return {"error": str(e)}

        retrieved = 0
        skipped = 0
        failed = 0

        for ad_data in scraped_ads:
            ad_library_id = ad_data.get("ad_library_id")
            if not ad_library_id:
                failed += 1
                continue

            existing = (
                session.query(Ad)
                .filter(Ad.ad_library_id == ad_library_id)
                .first()
            )

            if existing:
                skipped += 1
                continue

            try:
                snapshot_url = ad_data.get("ad_snapshot_url")
                creative_type = ad_data.get("creative_type", "image")

                if snapshot_url:
                    storage_path, detected_type = asyncio.run(
                        downloader.download_creative(
                            snapshot_url,
                            competitor.id,
                            ad_library_id,
                        )
                    )
                    download_status = "completed"
                    if detected_type:
                        creative_type = detected_type
                else:
                    storage_path = f"pending/{ad_library_id}"
                    download_status = "pending"

                ad = Ad(
                    competitor_id=competitor.id,
                    ad_library_id=ad_library_id,
                    ad_snapshot_url=snapshot_url,
                    creative_type=creative_type,
                    creative_storage_path=storage_path,
                    ad_copy=ad_data.get("ad_copy"),
                    ad_headline=ad_data.get("ad_headline"),
                    ad_description=ad_data.get("ad_description"),
                    cta_text=ad_data.get("cta_text"),
                    publication_date=ad_data.get("publication_date"),
                    download_status=download_status,
                    is_carousel=ad_data.get("is_carousel", False),
                    carousel_item_count=ad_data.get("carousel_item_count"),
                    landing_page_url=ad_data.get("landing_page_url"),
                    is_active=ad_data.get("is_active", True),
                )
                session.add(ad)
                retrieved += 1

            except CreativeDownloadError as e:
                logger.warning(
                    f"Failed to download creative for ad {ad_library_id}: {e}"
                )
                failed += 1
            except Exception as e:
                logger.warning(f"Failed to process ad {ad_library_id}: {e}")
                failed += 1

        competitor.last_retrieved = datetime.utcnow()
        session.commit()

        logger.info(
            f"Retrieved ads for {competitor.company_name}: "
            f"{retrieved} new, {skipped} skipped, {failed} failed"
        )

        return {
            "status": "completed",
            "competitor_id": competitor_id,
            "retrieved": retrieved,
            "skipped": skipped,
            "failed": failed,
        }

    except Exception as e:
        logger.error(f"Failed to retrieve ads for {competitor_id}: {e}")
        self.retry(exc=e, countdown=60 * 5)

    finally:
        session.close()
