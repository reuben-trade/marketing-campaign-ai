"""Competitor discovery background tasks."""

import asyncio
import logging
from datetime import datetime

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
def discover_competitors_task(self, max_competitors: int = 10):
    """
    Discover new competitors based on business strategy.

    This task runs monthly to find new competitors.
    """
    from app.models.analysis_run import AnalysisRun
    from app.models.business_strategy import BusinessStrategy
    from app.models.competitor import Competitor
    from app.services.competitor_discovery import CompetitorDiscovery

    session = get_sync_session()

    run = AnalysisRun(
        run_type="competitor_discovery",
        status="running",
        parameters={"max_competitors": max_competitors},
    )
    session.add(run)
    session.commit()

    try:
        strategy = (
            session.query(BusinessStrategy).order_by(BusinessStrategy.last_updated.desc()).first()
        )

        if not strategy:
            run.status = "failed"
            run.error_message = "No business strategy found"
            session.commit()
            return {"error": "No business strategy found"}

        from app.services.ad_library_scraper import AdLibraryScraper

        discovery = CompetitorDiscovery()
        discovered = asyncio.run(
            discovery.discover_competitors(
                business_name=strategy.business_name,
                industry=strategy.industry,
                business_description=strategy.business_description,
                market_position=strategy.market_position,
                max_competitors=max_competitors,
            )
        )

        added = 0
        skipped = 0
        manual_review = 0

        # Batch search for Facebook page IDs
        company_names = [comp["company_name"] for comp in discovered if comp.get("company_name")]
        scraper = AdLibraryScraper()
        page_id_results = asyncio.run(scraper.batch_search_page_ids(company_names))

        for comp_data in discovered:
            company_name = comp_data.get("company_name")
            page_id, facebook_url = page_id_results.get(company_name, (None, None))

            if not page_id:
                manual_review += 1
                continue

            existing = session.query(Competitor).filter(Competitor.page_id == page_id).first()

            if existing:
                skipped += 1
                continue

            competitor = Competitor(
                company_name=comp_data["company_name"],
                page_id=page_id,
                industry=strategy.industry,
                market_position=comp_data.get("market_position"),
                discovery_method="automated",
                metadata_={
                    "relevance_reason": comp_data.get("relevance_reason"),
                    "estimated_follower_range": comp_data.get("estimated_follower_range"),
                    "facebook_url": facebook_url,
                },
            )
            session.add(competitor)
            added += 1

        session.commit()

        run.status = "completed"
        run.items_processed = added
        run.items_failed = skipped
        run.completed_at = datetime.utcnow()
        run.logs = {
            "total_discovered": len(discovered),
            "added": added,
            "skipped": skipped,
            "manual_review": manual_review,
        }
        session.commit()

        logger.info(
            f"Competitor discovery completed: {added} added, {skipped} skipped, {manual_review} need manual review"
        )

        return {
            "status": "completed",
            "added": added,
            "skipped": skipped,
            "manual_review": manual_review,
            "total_discovered": len(discovered),
        }

    except Exception as e:
        logger.error(f"Competitor discovery failed: {e}")
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()
        session.commit()

        self.retry(exc=e, countdown=60 * 5)

    finally:
        session.close()


@celery_app.task
def enrich_competitor_task(competitor_id: str):
    """
    Enrich a competitor's data with additional information.

    This task can be triggered manually for individual competitors.
    """
    from uuid import UUID

    from app.models.competitor import Competitor
    from app.services.competitor_discovery import CompetitorDiscovery

    session = get_sync_session()

    try:
        competitor = session.query(Competitor).filter(Competitor.id == UUID(competitor_id)).first()

        if not competitor:
            return {"error": "Competitor not found"}

        _discovery = CompetitorDiscovery()  # noqa: F841 - disabled temporarily
        # enriched_data = asyncio.run(
        #     discovery.enrich_competitor_data(
        #         competitor.company_name,
        #         competitor.industry,
        #     )
        # )
        enriched_data = None  # taking too long to enrich all

        if enriched_data:
            competitor.metadata_ = competitor.metadata_ or {}
            competitor.metadata_.update(enriched_data)
            session.commit()

        logger.info(f"Enriched competitor {competitor_id}")

        return {"status": "completed", "enriched_data": enriched_data}

    except Exception as e:
        logger.error(f"Failed to enrich competitor {competitor_id}: {e}")
        return {"error": str(e)}

    finally:
        session.close()
