"""Add video_intelligence JSONB column for enhanced video analysis.

Revision ID: 007
Revises: 006
Create Date: 2026-01-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add video_intelligence JSONB column for storing "Creative DNA"
    # This stores the enhanced analysis with natural beats, cinematics,
    # and rhetorical appeal data for AI critiques without re-running video analysis
    op.add_column(
        "ads",
        sa.Column("video_intelligence", JSONB, nullable=True),
    )

    # Add GIN index for efficient JSONB queries
    op.create_index(
        "idx_ads_video_intelligence",
        "ads",
        ["video_intelligence"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_ads_video_intelligence", table_name="ads")
    op.drop_column("ads", "video_intelligence")
