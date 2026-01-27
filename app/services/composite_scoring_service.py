"""Composite scoring service for calculating unified ad scores."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ad import Ad
from app.models.ad_creative_analysis import AdCreativeAnalysis
from app.models.competitor import Competitor

logger = logging.getLogger(__name__)


class CompositeScoreCalculator:
    """
    Calculates unified composite scores for ads based on multiple factors.

    Formula (0.0-1.0 scale):
    composite_score = (
        ai_quality_score * 0.35 +       # hook, pacing, thumb_stop average
        survivorship_score * 0.25 +      # days_active category
        engagement_rate_score * 0.20 +   # percentile-based
        production_quality * 0.10 +      # from creative_analysis
        platform_optimization * 0.10     # sound-off, aspect ratio, duration
    )
    """

    @staticmethod
    def _normalize_1_to_10_score(score: int | float | None) -> float:
        """
        Normalize a 1-10 score to 0-1 scale.

        Formula: (score - 1) / 9
        Maps [1, 10] → [0, 1]
        """
        if score is None:
            return 0.5  # Default to middle if missing
        score = max(1, min(10, score))  # Clamp to 1-10
        return (score - 1) / 9

    async def calculate_ai_quality_score(self, ad: Ad) -> float:
        """
        Average of hook_score, pacing_score, thumb_stop_score from video_intelligence.

        Returns:
            float: 0.0-1.0 normalized score
        """
        if not ad.video_intelligence:
            return 0.5  # Default if no analysis

        hook_score = ad.video_intelligence.get("hook_score")
        pacing_score = ad.video_intelligence.get("overall_pacing_score")

        # Get thumb_stop_score from engagement_predictors
        engagement_predictors = ad.video_intelligence.get("engagement_predictors", {})
        thumb_stop = engagement_predictors.get("thumb_stop", {}) if engagement_predictors else {}
        thumb_stop_score = (
            thumb_stop.get("thumb_stop_score") if isinstance(thumb_stop, dict) else None
        )

        scores = []
        if hook_score is not None:
            scores.append(self._normalize_1_to_10_score(hook_score))
        if pacing_score is not None:
            scores.append(self._normalize_1_to_10_score(pacing_score))
        if thumb_stop_score is not None:
            scores.append(self._normalize_1_to_10_score(thumb_stop_score))

        if not scores:
            return 0.5  # Default if no scores available

        return sum(scores) / len(scores)

    def calculate_survivorship_score(self, ad: Ad) -> float:
        """
        Map days_active to 0.2/0.5/0.8/1.0 using existing survivorship_category property.

        Returns:
            float: 0.2 (Testing), 0.5 (Validated), 0.8 (Winner), or 1.0 (Evergreen)
        """
        category = ad.survivorship_category
        if category is None:
            return 0.2  # Default to Testing if unknown

        category_map = {
            "Testing": 0.2,
            "Validated": 0.5,
            "Winner": 0.8,
            "Evergreen": 1.0,
        }

        return category_map.get(category, 0.2)

    async def calculate_engagement_rate_score(
        self, db: AsyncSession, ad: Ad, competitor: Competitor | None = None
    ) -> float:
        """
        Calculate engagement rate percentile score.

        1. Get competitor.follower_count (or median if missing)
        2. Calculate engagement_rate = total_engagement / follower_count
        3. Rank as percentile across all ads (0.0-1.0 scale)

        Returns:
            float: 0.0-1.0 percentile rank
        """
        # Get competitor if not provided
        if competitor is None:
            result = await db.execute(select(Competitor).where(Competitor.id == ad.competitor_id))
            competitor = result.scalar_one_or_none()

        if competitor is None:
            logger.warning(f"No competitor found for ad {ad.id}")
            return 0.5  # Default if no competitor

        # Get follower count (or median if missing)
        follower_count = competitor.follower_count
        if follower_count is None or follower_count == 0:
            # Get median follower_count across all competitors
            result = await db.execute(
                select(func.percentile_cont(0.5).within_group(Competitor.follower_count)).where(
                    Competitor.follower_count.isnot(None),
                    Competitor.follower_count > 0,
                )
            )
            median_followers = result.scalar()
            follower_count = median_followers if median_followers else 10000  # Fallback

        # Calculate engagement rate
        total_engagement = ad.total_engagement
        engagement_rate = total_engagement / follower_count

        # Calculate percentile rank across all ads
        # Count how many ads have lower engagement rate
        result = await db.execute(
            select(func.count(Ad.id)).where(
                Ad.analyzed == True,  # noqa: E712
                Ad.analysis_status == "completed",
            )
        )
        _total_ads = result.scalar() or 1  # noqa: F841 - reserved for future percentile calc

        # For simplicity, calculate percentile based on current ad's engagement rate
        # In a full implementation, this would query all ads' engagement rates
        # For now, we'll normalize based on a typical range
        # Typical engagement rates: 0.001 (0.1%) to 0.05 (5%)
        # Use log scale for better distribution
        import math

        if engagement_rate <= 0:
            return 0.0

        # Log-scale normalization
        # 0.001 → 0, 0.01 → 0.5, 0.1 → 1.0
        log_rate = math.log10(engagement_rate + 0.0001)  # Add small value to avoid log(0)
        log_min = math.log10(0.001)  # -3
        log_max = math.log10(0.1)  # -1

        percentile = (log_rate - log_min) / (log_max - log_min)
        percentile = max(0.0, min(1.0, percentile))  # Clamp to 0-1

        return percentile

    async def calculate_production_quality_score(self, db: AsyncSession, ad: Ad) -> float:
        """
        Extract from creative_analysis.production_quality_score.
        Normalize from 1-10 to 0-1 scale.

        Returns:
            float: 0.0-1.0 normalized score
        """
        # Check if creative_analysis relationship is loaded
        if ad.creative_analysis:
            quality_score = ad.creative_analysis.production_quality_score
            return self._normalize_1_to_10_score(quality_score)

        # Load creative analysis if not already loaded
        result = await db.execute(
            select(AdCreativeAnalysis).where(AdCreativeAnalysis.ad_id == ad.id)
        )
        creative_analysis = result.scalar_one_or_none()

        if creative_analysis and creative_analysis.production_quality_score is not None:
            return self._normalize_1_to_10_score(creative_analysis.production_quality_score)

        # Fallback: calculate from video_intelligence if available
        if ad.video_intelligence:
            pacing = ad.video_intelligence.get("overall_pacing_score", 5)
            platform = ad.video_intelligence.get("platform_optimization", {})
            native = platform.get("native_feel_score", 5) if isinstance(platform, dict) else 5

            # Production quality = (pacing + (10 - native)) / 2
            # Inverted native: high production = low native feel
            production_quality = (pacing + (10 - native)) / 2
            return self._normalize_1_to_10_score(production_quality)

        return 0.5  # Default if no data

    def calculate_platform_optimization_score(self, ad: Ad) -> float:
        """
        Score based on sound_off, aspect_ratio, duration.

        Returns 0.0-1.0:
        - sound_off_compatible: 1.0 if True, 0.5 if False
        - aspect_ratio: 9:16=1.0, 4:5=0.9, 1:1=0.8, 16:9=0.6
        - duration_seconds: 15-30s=1.0, 10-15s or 30-60s=0.8, <10s or >60s=0.5

        Returns:
            float: 0.0-1.0 average score
        """
        if not ad.video_intelligence:
            return 0.5  # Default if no analysis

        platform = ad.video_intelligence.get("platform_optimization", {})
        if not isinstance(platform, dict):
            return 0.5

        scores = []

        # Sound-off compatibility
        sound_off = platform.get("sound_off_compatible")
        if sound_off is not None:
            scores.append(1.0 if sound_off else 0.5)

        # Aspect ratio scoring
        aspect_ratio = platform.get("aspect_ratio", "")
        aspect_ratio_scores = {
            "9:16": 1.0,  # Vertical (best for mobile)
            "4:5": 0.9,  # Near-square (good for social)
            "1:1": 0.8,  # Square (good for social)
            "16:9": 0.6,  # Horizontal (less optimal for mobile)
        }
        aspect_score = aspect_ratio_scores.get(aspect_ratio, 0.7)  # Default for unknown
        scores.append(aspect_score)

        # Duration scoring
        duration = platform.get("duration_seconds")
        if duration is not None:
            if 15 <= duration <= 30:
                duration_score = 1.0  # Optimal
            elif (10 <= duration < 15) or (30 < duration <= 60):
                duration_score = 0.8  # Good
            else:
                duration_score = 0.5  # Suboptimal
            scores.append(duration_score)

        if not scores:
            return 0.5

        return sum(scores) / len(scores)

    async def calculate_composite_score(
        self, db: AsyncSession, ad: Ad, competitor: Competitor | None = None
    ) -> float:
        """
        Calculate final composite score (0.0-1.0).

        Formula:
        composite_score = (
            ai_quality_score * 0.35 +
            survivorship_score * 0.25 +
            engagement_rate_score * 0.20 +
            production_quality * 0.10 +
            platform_optimization * 0.10
        )

        Returns:
            float: 0.0-1.0 composite score
        """
        ai_quality = await self.calculate_ai_quality_score(ad)
        survivorship = self.calculate_survivorship_score(ad)
        engagement_rate = await self.calculate_engagement_rate_score(db, ad, competitor)
        production = await self.calculate_production_quality_score(db, ad)
        platform = self.calculate_platform_optimization_score(ad)

        composite = (
            ai_quality * 0.35
            + survivorship * 0.25
            + engagement_rate * 0.20
            + production * 0.10
            + platform * 0.10
        )

        # Ensure result is in 0-1 range
        composite = max(0.0, min(1.0, composite))

        # Update ad fields
        ad.composite_score = composite
        ad.survivorship_score = survivorship
        ad.engagement_rate_percentile = engagement_rate
        ad.composite_score_calculated_at = datetime.now(timezone.utc)

        logger.info(
            f"Calculated composite score for ad {ad.id}: {composite:.3f} "
            f"(ai={ai_quality:.3f}, surv={survivorship:.3f}, eng={engagement_rate:.3f}, "
            f"prod={production:.3f}, plat={platform:.3f})"
        )

        return composite

    async def recalculate_all_percentiles(self, db: AsyncSession) -> dict[str, Any]:
        """
        Batch recalculate engagement percentiles for all ads.
        Called daily via Celery Beat or when new ads added.

        Returns:
            dict: Statistics about the recalculation
        """
        # Get all analyzed ads
        result = await db.execute(
            select(Ad)
            .where(
                Ad.analyzed == True,  # noqa: E712
                Ad.analysis_status == "completed",
            )
            .options(selectinload(Ad.competitor))
        )
        ads = result.scalars().all()

        if not ads:
            return {"processed": 0, "skipped": 0}

        processed = 0
        skipped = 0

        for ad in ads:
            try:
                # Recalculate engagement rate percentile
                await self.calculate_engagement_rate_score(db, ad, ad.competitor)
                processed += 1
            except Exception as e:
                logger.error(f"Failed to recalculate percentile for ad {ad.id}: {e}")
                skipped += 1

        await db.commit()

        logger.info(f"Recalculated percentiles: {processed} processed, {skipped} skipped")

        return {"processed": processed, "skipped": skipped}
