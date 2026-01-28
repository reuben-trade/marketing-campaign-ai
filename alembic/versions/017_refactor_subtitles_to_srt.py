"""Refactor subtitles from per-segment word timestamps to global SRT format.

Revision ID: 017
Revises: 016
Create Date: 2026-01-28

This migration:
- Adds srt_content TEXT column to project_files for storing full video SRT
- Removes transcript_words JSONB column from user_video_segments
- Keeps transcript_text on segments (populated by post-processing task)
- Keeps speaker_label on segments (extracted from SRT speaker tags)
- Keeps has_speech boolean on segments
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add srt_content to project_files for storing global video SRT
    op.add_column(
        "project_files",
        sa.Column("srt_content", sa.Text(), nullable=True),
    )

    # Remove transcript_words from user_video_segments
    # (global SRT on project_files replaces per-segment word timestamps)
    op.drop_column("user_video_segments", "transcript_words")


def downgrade() -> None:
    # Re-add transcript_words column to user_video_segments
    op.add_column(
        "user_video_segments",
        sa.Column(
            "transcript_words",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Remove srt_content from project_files
    op.drop_column("project_files", "srt_content")
