"""Add duplicate tracking fields for ad creatives.

Revision ID: 006
Revises: 005
Create Date: 2026-01-21

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add perceptual hash for duplicate detection
    op.add_column(
        "ads",
        sa.Column("perceptual_hash", sa.String(256), nullable=True),
    )

    # Add reference to original ad (for duplicates)
    op.add_column(
        "ads",
        sa.Column(
            "original_ad_id",
            sa.Uuid,
            sa.ForeignKey("ads.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Add duplicate count (tracked on originals)
    op.add_column(
        "ads",
        sa.Column("duplicate_count", sa.Integer, nullable=False, server_default="1"),
    )

    # Add indexes for efficient lookups
    op.create_index("idx_ads_perceptual_hash", "ads", ["perceptual_hash"])
    op.create_index("idx_ads_original_ad_id", "ads", ["original_ad_id"])


def downgrade() -> None:
    op.drop_index("idx_ads_original_ad_id", table_name="ads")
    op.drop_index("idx_ads_perceptual_hash", table_name="ads")
    op.drop_column("ads", "duplicate_count")
    op.drop_column("ads", "original_ad_id")
    op.drop_column("ads", "perceptual_hash")
