#!/usr/bin/env python
"""Backfill ad_creative_analysis and ad_elements tables from existing video_intelligence data."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import async_session_maker  # noqa: E402
from app.models.ad import Ad  # noqa: E402
from app.services.creative_analysis_service import backfill_existing_ads  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Backfill creative analysis and elements for all ads with video_intelligence."""
    logger.info("Starting backfill of ad_creative_analysis and ad_elements tables...")

    async with async_session_maker() as db:
        # Get all ads that have video_intelligence data
        result = await db.execute(select(Ad).where(Ad.video_intelligence.isnot(None)))
        ads = result.scalars().all()

        logger.info(f"Found {len(ads)} ads with video_intelligence data")

        if not ads:
            logger.info("No ads to process")
            return

        # Run backfill
        stats = await backfill_existing_ads(db, list(ads))

        logger.info("Backfill complete!")
        logger.info(f"  Processed: {stats['processed']}")
        logger.info(f"  Skipped (no data): {stats['skipped']}")
        logger.info(f"  Failed: {stats['failed']}")


if __name__ == "__main__":
    asyncio.run(main())
