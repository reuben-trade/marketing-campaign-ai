"""Add critiques table for persisting user ad feedback.

Revision ID: 010
Revises: 009
Create Date: 2026-01-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "critiques",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("media_type", sa.String(10), nullable=False),  # 'image' or 'video'
        # User-provided context
        sa.Column("brand_name", sa.String(255), nullable=True),
        sa.Column("industry", sa.String(255), nullable=True),
        sa.Column("target_audience", sa.Text, nullable=True),
        sa.Column("platform_cta", sa.String(255), nullable=True),
        # Analysis results (full EnhancedAdAnalysisV2 as JSONB)
        sa.Column("analysis", JSONB, nullable=False),
        # Denormalized top-level scores for listing/filtering
        sa.Column("overall_grade", sa.String(5), nullable=True),
        sa.Column("hook_score", sa.Integer, nullable=True),
        sa.Column("pacing_score", sa.Integer, nullable=True),
        sa.Column("thumb_stop_score", sa.Integer, nullable=True),
        sa.Column("analysis_confidence", sa.Numeric(3, 2), nullable=True),
        # Processing metadata
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("processing_time_seconds", sa.Numeric(10, 2), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes
    op.create_index("idx_critiques_created_at", "critiques", ["created_at"])
    op.create_index("idx_critiques_media_type", "critiques", ["media_type"])
    op.create_index("idx_critiques_overall_grade", "critiques", ["overall_grade"])


def downgrade() -> None:
    op.drop_index("idx_critiques_overall_grade")
    op.drop_index("idx_critiques_media_type")
    op.drop_index("idx_critiques_created_at")
    op.drop_table("critiques")
