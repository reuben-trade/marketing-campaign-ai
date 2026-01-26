"""Add composite scoring and embeddings with pgvector.

Revision ID: 012
Revises: 011
Create Date: 2026-01-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (Supabase has this by default, but safe to run)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add composite scoring fields (all on 0-1 scale)
    op.add_column(
        "ads",
        sa.Column("composite_score", sa.Float(), nullable=True, comment="Range: 0.0 to 1.0"),
    )
    op.add_column(
        "ads",
        sa.Column("composite_score_calculated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ads",
        sa.Column(
            "engagement_rate_percentile",
            sa.Float(),
            nullable=True,
            comment="Range: 0.0 to 1.0 - percentile rank across all ads",
        ),
    )
    op.add_column(
        "ads",
        sa.Column(
            "survivorship_score",
            sa.Float(),
            nullable=True,
            comment="Range: 0.2/0.5/0.8/1.0 based on days_active",
        ),
    )

    # Add semantic search fields
    op.add_column(
        "ads",
        sa.Column("ad_summary", sa.Text(), nullable=True, comment="Generated summary for embeddings"),
    )
    op.add_column(
        "ads",
        sa.Column(
            "embedding",
            Vector(1536),
            nullable=True,
            comment="1536-dim OpenAI embedding using pgvector",
        ),
    )

    # Create indexes for composite scores
    op.create_index("idx_ads_composite_score", "ads", ["composite_score"])
    op.create_index("idx_ads_engagement_rate_percentile", "ads", ["engagement_rate_percentile"])

    # Create HNSW index for fast similarity search
    # HNSW = Hierarchical Navigable Small World graph
    # m=16: number of connections per layer (trade-off: higher=more accurate but slower)
    # ef_construction=64: size of dynamic candidate list (trade-off: higher=better index quality but slower build)
    op.execute(
        """
        CREATE INDEX ads_embedding_hnsw_idx
        ON ads
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """
    )


def downgrade() -> None:
    # Drop HNSW index
    op.drop_index("ads_embedding_hnsw_idx", "ads")

    # Drop regular indexes
    op.drop_index("idx_ads_engagement_rate_percentile", "ads")
    op.drop_index("idx_ads_composite_score", "ads")

    # Drop columns
    op.drop_column("ads", "embedding")
    op.drop_column("ads", "ad_summary")
    op.drop_column("ads", "survivorship_score")
    op.drop_column("ads", "engagement_rate_percentile")
    op.drop_column("ads", "composite_score_calculated_at")
    op.drop_column("ads", "composite_score")

    # Drop pgvector extension (commented out to be safe - other tables might use it)
    # op.execute("DROP EXTENSION IF EXISTS vector")
