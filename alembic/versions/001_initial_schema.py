"""Initial schema with all tables.

Revision ID: 001
Revises:
Create Date: 2026-01-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create business_strategy table
    op.create_table(
        "business_strategy",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("business_description", sa.Text, nullable=True),
        sa.Column("industry", sa.String(255), nullable=True),
        sa.Column("target_audience", postgresql.JSONB, nullable=True),
        sa.Column("brand_voice", postgresql.JSONB, nullable=True),
        sa.Column("market_position", sa.String(50), nullable=True),
        sa.Column("price_point", sa.String(50), nullable=True),
        sa.Column("business_life_stage", sa.String(50), nullable=True),
        sa.Column("unique_selling_points", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("competitive_advantages", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("marketing_objectives", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("raw_pdf_url", sa.Text, nullable=True),
        sa.Column("extracted_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create competitors table
    op.create_table(
        "competitors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("ad_library_url", sa.Text, nullable=False, unique=True),
        sa.Column("industry", sa.String(255), nullable=True),
        sa.Column("follower_count", sa.Integer, nullable=True),
        sa.Column("is_market_leader", sa.Boolean, server_default=sa.text("false")),
        sa.Column("market_position", sa.String(50), nullable=True),
        sa.Column("discovery_method", sa.String(50), nullable=True),
        sa.Column("discovered_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_retrieved", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )
    op.create_index("idx_competitors_active", "competitors", ["active"])
    op.create_index("idx_competitors_last_retrieved", "competitors", ["last_retrieved"])

    # Create ads table
    op.create_table(
        "ads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "competitor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("competitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ad_library_id", sa.String(255), nullable=False, unique=True),
        sa.Column("ad_snapshot_url", sa.Text, nullable=True),
        sa.Column("creative_type", sa.String(20), nullable=False),
        sa.Column("creative_storage_path", sa.Text, nullable=False),
        sa.Column("creative_url", sa.Text, nullable=True),
        sa.Column("ad_copy", sa.Text, nullable=True),
        sa.Column("ad_headline", sa.Text, nullable=True),
        sa.Column("ad_description", sa.Text, nullable=True),
        sa.Column("cta_text", sa.String(255), nullable=True),
        sa.Column("likes", sa.Integer, server_default=sa.text("0")),
        sa.Column("comments", sa.Integer, server_default=sa.text("0")),
        sa.Column("shares", sa.Integer, server_default=sa.text("0")),
        sa.Column("impressions", sa.Integer, nullable=True),
        sa.Column("analysis", postgresql.JSONB, nullable=True),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("analyzed_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analyzed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("download_status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("analysis_status", sa.String(20), server_default=sa.text("'pending'")),
    )
    op.create_index("idx_ads_competitor", "ads", ["competitor_id"])
    op.create_index("idx_ads_analyzed", "ads", ["analyzed"])
    op.create_index("idx_ads_creative_type", "ads", ["creative_type"])
    op.create_index(
        "idx_ads_publication_date",
        "ads",
        ["publication_date"],
        postgresql_ops={"publication_date": "DESC"},
    )

    # Create recommendations table
    op.create_table(
        "recommendations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("generated_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("top_n_ads", sa.Integer, nullable=True),
        sa.Column("date_range_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_range_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trend_analysis", postgresql.JSONB, nullable=True),
        sa.Column("recommendations", postgresql.JSONB, nullable=True),
        sa.Column("executive_summary", postgresql.JSONB, nullable=True),
        sa.Column("implementation_roadmap", postgresql.JSONB, nullable=True),
        sa.Column("ads_analyzed", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("generation_time_seconds", sa.Numeric(10, 2), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
    )

    # Create analysis_runs table
    op.create_table(
        "analysis_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("run_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default=sa.text("'pending'")),
        sa.Column("items_processed", sa.Integer, server_default=sa.text("0")),
        sa.Column("items_failed", sa.Integer, server_default=sa.text("0")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("parameters", postgresql.JSONB, nullable=True),
        sa.Column("logs", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("analysis_runs")
    op.drop_table("recommendations")
    op.drop_index("idx_ads_publication_date", table_name="ads")
    op.drop_index("idx_ads_creative_type", table_name="ads")
    op.drop_index("idx_ads_analyzed", table_name="ads")
    op.drop_index("idx_ads_competitor", table_name="ads")
    op.drop_table("ads")
    op.drop_index("idx_competitors_last_retrieved", table_name="competitors")
    op.drop_index("idx_competitors_active", table_name="competitors")
    op.drop_table("competitors")
    op.drop_table("business_strategy")
