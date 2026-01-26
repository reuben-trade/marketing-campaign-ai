"""Service for populating ad_creative_analysis and ad_elements tables from video_intelligence."""

import logging
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad import Ad
from app.models.ad_creative_analysis import AdCreativeAnalysis
from app.models.ad_element import AdElement

logger = logging.getLogger(__name__)


def parse_time_to_seconds(time_str: str | None) -> float | None:
    """Convert MM:SS format to seconds."""
    if not time_str:
        return None
    try:
        parts = time_str.split(":")
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        return float(time_str)
    except (ValueError, AttributeError):
        return None


def calculate_duration(start_time: str | None, end_time: str | None) -> float | None:
    """Calculate duration from start and end time strings."""
    start_seconds = parse_time_to_seconds(start_time)
    end_seconds = parse_time_to_seconds(end_time)
    if start_seconds is not None and end_seconds is not None:
        return end_seconds - start_seconds
    return None


async def populate_creative_analysis(
    db: AsyncSession,
    ad: Ad,
    video_intelligence: dict[str, Any],
) -> AdCreativeAnalysis:
    """
    Create or update AdCreativeAnalysis from video_intelligence data.

    Args:
        db: Database session
        ad: The Ad model instance
        video_intelligence: The parsed EnhancedAdAnalysisV2 dict

    Returns:
        The created/updated AdCreativeAnalysis instance
    """
    # Extract nested data
    copy_analysis = video_intelligence.get("copy_analysis", {}) or {}
    audio_analysis = video_intelligence.get("audio_analysis", {}) or {}
    brand_elements = video_intelligence.get("brand_elements", {}) or {}
    engagement = video_intelligence.get("engagement_predictors", {}) or {}
    thumb_stop = engagement.get("thumb_stop", {}) or {}
    platform = video_intelligence.get("platform_optimization", {}) or {}
    critique = video_intelligence.get("critique", {}) or {}
    emotional_arc = video_intelligence.get("emotional_arc", {}) or {}
    music = audio_analysis.get("music", {}) or {}
    voice = audio_analysis.get("voice", {}) or {}

    # Check if analysis already exists (query to avoid lazy load issues)
    result = await db.execute(select(AdCreativeAnalysis).where(AdCreativeAnalysis.ad_id == ad.id))
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing record
        analysis = existing
    else:
        # Create new record
        analysis = AdCreativeAnalysis(ad_id=ad.id)
        db.add(analysis)

    # Core analysis scores
    analysis.hook_score = video_intelligence.get("hook_score")
    analysis.overall_pacing_score = video_intelligence.get("overall_pacing_score")
    analysis.production_style = video_intelligence.get("production_style")

    # Audience and messaging
    analysis.inferred_audience = video_intelligence.get("inferred_audience")
    analysis.primary_messaging_pillar = video_intelligence.get("primary_messaging_pillar")
    analysis.overall_narrative_summary = video_intelligence.get("overall_narrative_summary")

    # Copy analysis
    analysis.copy_framework = copy_analysis.get("copy_framework")
    analysis.headline_text = copy_analysis.get("headline_text")
    analysis.cta_text = copy_analysis.get("cta_text")
    analysis.power_words = copy_analysis.get("power_words")

    # Engagement predictors
    analysis.thumb_stop_score = thumb_stop.get("thumb_stop_score")
    analysis.curiosity_gap = thumb_stop.get("curiosity_gap")
    analysis.uses_social_proof = engagement.get("uses_social_proof_signals")
    analysis.uses_fomo = engagement.get("uses_fear_of_missing_out")
    analysis.uses_transformation = engagement.get("uses_transformation_narrative")

    # Platform optimization
    analysis.aspect_ratio = platform.get("aspect_ratio")
    analysis.sound_off_compatible = platform.get("sound_off_compatible")
    analysis.native_feel_score = platform.get("native_feel_score")
    analysis.duration_seconds = platform.get("duration_seconds")

    # Critique
    analysis.overall_grade = critique.get("overall_grade")

    # Audio (video only)
    analysis.has_voiceover = voice.get("has_voiceover")
    analysis.music_genre = music.get("genre")
    analysis.music_energy = music.get("energy_level")

    # Visual analysis (from brand_elements)
    analysis.color_palette = brand_elements.get("brand_colors_detected")
    analysis.has_product_shot = brand_elements.get("has_product_shot")
    analysis.has_human_face = thumb_stop.get("face_in_first_frame")

    # Emotional analysis
    analysis.primary_emotion = emotional_arc.get("dominant_emotional_tone")

    # Production quality score - derive from native_feel_score and pacing
    pacing = video_intelligence.get("overall_pacing_score", 5)
    native = platform.get("native_feel_score", 5)
    if pacing and native:
        # Invert native feel (10 = very native/UGC, so high production = low native)
        # Average with pacing for a rough production quality estimate
        production_quality = int((pacing + (10 - native)) / 2)
        analysis.production_quality_score = min(10, max(1, production_quality))

    # Map production_style to creative_archetype for backward compatibility
    style = video_intelligence.get("production_style", "")
    if style:
        archetype_map = {
            "High-production Studio": "High-Production Studio",
            "Authentic UGC": "UGC",
            "Hybrid": "Problem/Solution Demo",
            "Animation": "High-Production Studio",
            "Stock Footage Mashup": "Lo-fi Meme",
            "Screen Recording": "UGC",
            "Talking Head": "UGC",
            "Documentary Style": "High-Production Studio",
            "Influencer Native": "UGC",
        }
        analysis.creative_archetype = archetype_map.get(style, style)

    return analysis


async def populate_ad_elements(
    db: AsyncSession,
    ad: Ad,
    video_intelligence: dict[str, Any],
) -> list[AdElement]:
    """
    Create AdElement records from video_intelligence timeline data.

    Args:
        db: Database session
        ad: The Ad model instance
        video_intelligence: The parsed EnhancedAdAnalysisV2 dict

    Returns:
        List of created AdElement instances
    """
    timeline = video_intelligence.get("timeline", []) or []

    if not timeline:
        logger.debug(f"No timeline data for ad {ad.id}")
        return []

    # Delete existing elements for this ad (replace strategy)
    await db.execute(delete(AdElement).where(AdElement.ad_id == ad.id))

    elements = []
    for idx, beat in enumerate(timeline):
        cinematics = beat.get("cinematics", {}) or {}
        rhetorical = beat.get("rhetorical_appeal", {}) or {}

        element = AdElement(
            ad_id=ad.id,
            beat_index=idx,
            beat_type=beat.get("beat_type", "Unknown"),
            start_time=beat.get("start_time"),
            end_time=beat.get("end_time"),
            duration_seconds=calculate_duration(beat.get("start_time"), beat.get("end_time")),
            # Content
            visual_description=beat.get("visual_description"),
            audio_transcript=beat.get("audio_transcript"),
            tone_of_voice=beat.get("tone_of_voice"),
            # Emotion
            emotion=beat.get("emotion"),
            emotion_intensity=beat.get("emotion_intensity"),
            attention_score=beat.get("attention_score"),
            # Rhetorical
            rhetorical_mode=rhetorical.get("mode"),
            rhetorical_description=rhetorical.get("description"),
            persuasion_techniques=rhetorical.get("persuasion_techniques"),
            # Cinematics
            camera_angle=cinematics.get("camera_angle"),
            lighting_style=cinematics.get("lighting_style"),
            color_grading=cinematics.get("color_grading"),
            motion_type=cinematics.get("motion_type"),
            transition_in=cinematics.get("transition_in"),
            transition_out=cinematics.get("transition_out"),
            cinematic_features=cinematics.get("cinematic_features"),
            # Elements
            text_overlays=beat.get("text_overlays_in_beat"),
            key_visual_elements=beat.get("key_visual_elements"),
            target_audience_cues=beat.get("target_audience_cues"),
            improvement_note=beat.get("improvement_note"),
        )
        db.add(element)
        elements.append(element)

    logger.info(f"Created {len(elements)} elements for ad {ad.id}")
    return elements


async def populate_from_video_intelligence(
    db: AsyncSession,
    ad: Ad,
    video_intelligence: dict[str, Any] | None = None,
) -> tuple[AdCreativeAnalysis | None, list[AdElement]]:
    """
    Populate both ad_creative_analysis and ad_elements tables from video_intelligence.

    Args:
        db: Database session
        ad: The Ad model instance
        video_intelligence: Optional override; if not provided, uses ad.video_intelligence

    Returns:
        Tuple of (AdCreativeAnalysis, list[AdElement])
    """
    vi = video_intelligence or ad.video_intelligence

    if not vi:
        logger.warning(f"No video_intelligence data for ad {ad.id}")
        return None, []

    # Populate both tables
    analysis = await populate_creative_analysis(db, ad, vi)
    elements = await populate_ad_elements(db, ad, vi)

    return analysis, elements


async def backfill_existing_ads(
    db: AsyncSession,
    ads: list[Ad],
) -> dict[str, int]:
    """
    Backfill ad_creative_analysis and ad_elements for ads that already have video_intelligence.

    Args:
        db: Database session
        ads: List of Ad instances to process

    Returns:
        Dict with counts: {"processed": N, "skipped": N, "failed": N}
    """
    processed = 0
    skipped = 0
    failed = 0

    for ad in ads:
        if not ad.video_intelligence:
            skipped += 1
            continue

        try:
            await populate_from_video_intelligence(db, ad)
            processed += 1
        except Exception as e:
            logger.error(f"Failed to populate analysis for ad {ad.id}: {e}")
            failed += 1

    await db.commit()

    return {
        "processed": processed,
        "skipped": skipped,
        "failed": failed,
    }
