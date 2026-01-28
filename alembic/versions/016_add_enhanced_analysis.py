"""Add enhanced video analysis fields: transcript, clip ordering, V2 analysis.

Revision ID: 016
Revises: 015
Create Date: 2026-01-28

Sprint 5 tasks:
- s5-t5: Add transcript extraction (transcript_text, transcript_words, speaker_label)
- s5-t6: Add clip ordering (previous_segment_id, next_segment_id, segment_index)
- s5-t7: Add V2 analysis fields (beat_type, attention_score, emotion_intensity, etc.)
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===========================================================================
    # Clip Ordering Fields (Doubly-Linked List)
    # ===========================================================================
    op.add_column(
        "user_video_segments",
        sa.Column(
            "previous_segment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_video_segments.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "user_video_segments",
        sa.Column(
            "next_segment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_video_segments.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "user_video_segments",
        sa.Column("segment_index", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "user_video_segments",
        sa.Column("total_segments_in_source", sa.Integer(), server_default="1", nullable=False),
    )

    # ===========================================================================
    # Transcript Fields
    # ===========================================================================
    op.add_column(
        "user_video_segments",
        sa.Column("transcript_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "user_video_segments",
        sa.Column(
            "transcript_words",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "user_video_segments",
        sa.Column("speaker_label", sa.String(20), nullable=True),
    )

    # ===========================================================================
    # V2 Analysis Fields
    # ===========================================================================
    op.add_column(
        "user_video_segments",
        sa.Column("beat_type", sa.String(30), nullable=True),
    )
    op.add_column(
        "user_video_segments",
        sa.Column("attention_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "user_video_segments",
        sa.Column("emotion_intensity", sa.Integer(), nullable=True),
    )
    op.add_column(
        "user_video_segments",
        sa.Column("color_grading", sa.String(30), nullable=True),
    )
    op.add_column(
        "user_video_segments",
        sa.Column("lighting_style", sa.String(30), nullable=True),
    )
    op.add_column(
        "user_video_segments",
        sa.Column("has_speech", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "user_video_segments",
        sa.Column(
            "power_words_detected",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # ===========================================================================
    # Index for Ordering Queries
    # ===========================================================================
    op.create_index(
        "idx_segments_ordering",
        "user_video_segments",
        ["source_file_id", "segment_index"],
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("idx_segments_ordering", table_name="user_video_segments")

    # Drop V2 analysis fields
    op.drop_column("user_video_segments", "power_words_detected")
    op.drop_column("user_video_segments", "has_speech")
    op.drop_column("user_video_segments", "lighting_style")
    op.drop_column("user_video_segments", "color_grading")
    op.drop_column("user_video_segments", "emotion_intensity")
    op.drop_column("user_video_segments", "attention_score")
    op.drop_column("user_video_segments", "beat_type")

    # Drop transcript fields
    op.drop_column("user_video_segments", "speaker_label")
    op.drop_column("user_video_segments", "transcript_words")
    op.drop_column("user_video_segments", "transcript_text")

    # Drop clip ordering fields
    op.drop_column("user_video_segments", "total_segments_in_source")
    op.drop_column("user_video_segments", "segment_index")
    op.drop_column("user_video_segments", "next_segment_id")
    op.drop_column("user_video_segments", "previous_segment_id")
