"""Expand ad_creative_analysis and add ad_elements table.

This migration:
1. Adds new columns to ad_creative_analysis for queryable top-level analysis data
2. Creates ad_elements table for granular timeline/narrative beat data

Revision ID: 008
Revises: 007
Create Date: 2026-01-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, JSONB

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # EXPAND ad_creative_analysis TABLE
    # =========================================================================

    # Core analysis scores
    op.add_column(
        "ad_creative_analysis",
        sa.Column("hook_score", sa.Integer(), nullable=True, comment="1-10 hook effectiveness"),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("overall_pacing_score", sa.Integer(), nullable=True, comment="1-10 pacing effectiveness"),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("production_style", sa.String(50), nullable=True, comment="UGC, Studio, Hybrid, etc."),
    )

    # Audience and messaging
    op.add_column(
        "ad_creative_analysis",
        sa.Column("inferred_audience", sa.Text(), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("primary_messaging_pillar", sa.String(100), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("overall_narrative_summary", sa.Text(), nullable=True),
    )

    # Copy analysis
    op.add_column(
        "ad_creative_analysis",
        sa.Column("copy_framework", sa.String(50), nullable=True, comment="PAS, AIDA, BAB, etc."),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("headline_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("cta_text", sa.String(255), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("power_words", JSON(), nullable=True),
    )

    # Engagement predictors
    op.add_column(
        "ad_creative_analysis",
        sa.Column("thumb_stop_score", sa.Integer(), nullable=True, comment="1-10 scroll-stop potential"),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("curiosity_gap", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("uses_social_proof", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("uses_fomo", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("uses_transformation", sa.Boolean(), nullable=True),
    )

    # Platform optimization
    op.add_column(
        "ad_creative_analysis",
        sa.Column("aspect_ratio", sa.String(10), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("sound_off_compatible", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("native_feel_score", sa.Integer(), nullable=True, comment="1-10 organic feel"),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("duration_seconds", sa.Float(), nullable=True),
    )

    # Critique
    op.add_column(
        "ad_creative_analysis",
        sa.Column("overall_grade", sa.String(5), nullable=True, comment="A+, B-, C, etc."),
    )

    # Audio (video only)
    op.add_column(
        "ad_creative_analysis",
        sa.Column("has_voiceover", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("music_genre", sa.String(50), nullable=True),
    )
    op.add_column(
        "ad_creative_analysis",
        sa.Column("music_energy", sa.String(50), nullable=True),
    )

    # Add useful indexes
    op.create_index("idx_aca_hook_score", "ad_creative_analysis", ["hook_score"])
    op.create_index("idx_aca_production_style", "ad_creative_analysis", ["production_style"])
    op.create_index("idx_aca_copy_framework", "ad_creative_analysis", ["copy_framework"])
    op.create_index("idx_aca_overall_grade", "ad_creative_analysis", ["overall_grade"])
    op.create_index("idx_aca_thumb_stop_score", "ad_creative_analysis", ["thumb_stop_score"])

    # =========================================================================
    # CREATE ad_elements TABLE
    # =========================================================================

    op.create_table(
        "ad_elements",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ad_id", sa.Uuid(), sa.ForeignKey("ads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("beat_index", sa.Integer(), nullable=False, comment="Position in timeline (0, 1, 2...)"),
        sa.Column("beat_type", sa.String(50), nullable=False, comment="Hook, Problem, Solution, CTA, etc."),
        sa.Column("start_time", sa.String(10), nullable=True, comment="MM:SS format"),
        sa.Column("end_time", sa.String(10), nullable=True, comment="MM:SS format"),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        # Content
        sa.Column("visual_description", sa.Text(), nullable=True),
        sa.Column("audio_transcript", sa.Text(), nullable=True),
        sa.Column("tone_of_voice", sa.String(100), nullable=True),
        # Emotion
        sa.Column("emotion", sa.String(50), nullable=True),
        sa.Column("emotion_intensity", sa.Integer(), nullable=True, comment="1-10"),
        sa.Column("attention_score", sa.Integer(), nullable=True, comment="1-10"),
        # Rhetorical
        sa.Column("rhetorical_mode", sa.String(20), nullable=True, comment="Logos, Pathos, Ethos, Kairos"),
        sa.Column("rhetorical_description", sa.Text(), nullable=True),
        sa.Column("persuasion_techniques", JSON(), nullable=True),
        # Cinematics
        sa.Column("camera_angle", sa.String(50), nullable=True),
        sa.Column("lighting_style", sa.String(50), nullable=True),
        sa.Column("color_grading", sa.String(50), nullable=True),
        sa.Column("motion_type", sa.String(50), nullable=True),
        sa.Column("transition_in", sa.String(50), nullable=True),
        sa.Column("transition_out", sa.String(50), nullable=True),
        sa.Column("cinematic_features", JSON(), nullable=True),
        # Elements
        sa.Column("text_overlays", JSON(), nullable=True, comment="Array of TextOverlay objects"),
        sa.Column("key_visual_elements", JSON(), nullable=True),
        sa.Column("target_audience_cues", sa.Text(), nullable=True),
        sa.Column("improvement_note", sa.Text(), nullable=True),
        # Metadata
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create indexes for ad_elements
    op.create_index("idx_ad_elements_ad_id", "ad_elements", ["ad_id"])
    op.create_index("idx_ad_elements_beat_type", "ad_elements", ["beat_type"])
    op.create_index("idx_ad_elements_ad_beat", "ad_elements", ["ad_id", "beat_index"])
    op.create_index("idx_ad_elements_emotion", "ad_elements", ["emotion"])
    op.create_index("idx_ad_elements_rhetorical_mode", "ad_elements", ["rhetorical_mode"])
    op.create_index("idx_ad_elements_attention_score", "ad_elements", ["attention_score"])


def downgrade() -> None:
    # Drop ad_elements table
    op.drop_index("idx_ad_elements_attention_score", table_name="ad_elements")
    op.drop_index("idx_ad_elements_rhetorical_mode", table_name="ad_elements")
    op.drop_index("idx_ad_elements_emotion", table_name="ad_elements")
    op.drop_index("idx_ad_elements_ad_beat", table_name="ad_elements")
    op.drop_index("idx_ad_elements_beat_type", table_name="ad_elements")
    op.drop_index("idx_ad_elements_ad_id", table_name="ad_elements")
    op.drop_table("ad_elements")

    # Drop ad_creative_analysis indexes
    op.drop_index("idx_aca_thumb_stop_score", table_name="ad_creative_analysis")
    op.drop_index("idx_aca_overall_grade", table_name="ad_creative_analysis")
    op.drop_index("idx_aca_copy_framework", table_name="ad_creative_analysis")
    op.drop_index("idx_aca_production_style", table_name="ad_creative_analysis")
    op.drop_index("idx_aca_hook_score", table_name="ad_creative_analysis")

    # Drop ad_creative_analysis columns
    op.drop_column("ad_creative_analysis", "music_energy")
    op.drop_column("ad_creative_analysis", "music_genre")
    op.drop_column("ad_creative_analysis", "has_voiceover")
    op.drop_column("ad_creative_analysis", "overall_grade")
    op.drop_column("ad_creative_analysis", "duration_seconds")
    op.drop_column("ad_creative_analysis", "native_feel_score")
    op.drop_column("ad_creative_analysis", "sound_off_compatible")
    op.drop_column("ad_creative_analysis", "aspect_ratio")
    op.drop_column("ad_creative_analysis", "uses_transformation")
    op.drop_column("ad_creative_analysis", "uses_fomo")
    op.drop_column("ad_creative_analysis", "uses_social_proof")
    op.drop_column("ad_creative_analysis", "curiosity_gap")
    op.drop_column("ad_creative_analysis", "thumb_stop_score")
    op.drop_column("ad_creative_analysis", "power_words")
    op.drop_column("ad_creative_analysis", "cta_text")
    op.drop_column("ad_creative_analysis", "headline_text")
    op.drop_column("ad_creative_analysis", "copy_framework")
    op.drop_column("ad_creative_analysis", "overall_narrative_summary")
    op.drop_column("ad_creative_analysis", "primary_messaging_pillar")
    op.drop_column("ad_creative_analysis", "inferred_audience")
    op.drop_column("ad_creative_analysis", "production_style")
    op.drop_column("ad_creative_analysis", "overall_pacing_score")
    op.drop_column("ad_creative_analysis", "hook_score")
