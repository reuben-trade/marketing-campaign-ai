"""Add landing_pages, ad_creative_analysis, cross_platform_ads tables and update ads.

Revision ID: 003
Revises: 002
Create Date: 2026-01-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create landing_pages table
    op.create_table(
        "landing_pages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("url", sa.Text, nullable=False, unique=True),
        sa.Column(
            "url_hash", sa.String(64), nullable=False, unique=True
        ),  # SHA256 hash for fast lookups
        sa.Column("final_url", sa.Text, nullable=True),  # URL after redirects
        # Content
        sa.Column("page_title", sa.Text, nullable=True),
        sa.Column("meta_description", sa.Text, nullable=True),
        sa.Column("meta_keywords", sa.Text, nullable=True),
        sa.Column("headings", postgresql.JSONB, nullable=True),  # {h1: [], h2: [], h3: []}
        sa.Column("content_preview", sa.Text, nullable=True),  # First ~500 chars of main content
        sa.Column("cta_buttons", postgresql.JSONB, nullable=True),  # [{text: "", href: ""}]
        # Technical metrics
        sa.Column("http_status_code", sa.Integer, nullable=True),
        sa.Column("load_time_ms", sa.Integer, nullable=True),
        # Screenshots
        sa.Column("desktop_screenshot_path", sa.Text, nullable=True),
        sa.Column("mobile_screenshot_path", sa.Text, nullable=True),
        # Tracking pixel detection
        sa.Column("meta_pixel_id", sa.String(50), nullable=True),
        sa.Column("has_capi", sa.Boolean, server_default=sa.text("false")),
        sa.Column("google_ads_tag_id", sa.String(50), nullable=True),
        sa.Column("tiktok_pixel_id", sa.String(50), nullable=True),
        sa.Column("technical_sophistication_score", sa.Integer, nullable=True),  # 0-100
        # Timestamps
        sa.Column("first_scraped_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("scrape_count", sa.Integer, server_default=sa.text("1")),
    )
    op.create_index("idx_landing_pages_url_hash", "landing_pages", ["url_hash"])
    op.create_index("idx_landing_pages_meta_pixel_id", "landing_pages", ["meta_pixel_id"])

    # Create ad_creative_analysis table
    op.create_table(
        "ad_creative_analysis",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "ad_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Creative archetype classification
        sa.Column(
            "creative_archetype", sa.String(50), nullable=True
        ),  # UGC, Problem/Solution Demo, Lo-fi Meme, High-Production Studio
        sa.Column("archetype_confidence", sa.Numeric(3, 2), nullable=True),  # 0.00-1.00
        # Hook/offer detection
        sa.Column(
            "hook_offer_type", sa.String(100), nullable=True
        ),  # Free Quote, 20% Discount, BOGO, etc.
        sa.Column("offer_details", sa.Text, nullable=True),  # Specific offer text extracted
        sa.Column("offer_confidence", sa.Numeric(3, 2), nullable=True),
        # Emotional analysis
        sa.Column(
            "primary_emotion", sa.String(50), nullable=True
        ),  # urgency, aspiration, fear, belonging, curiosity
        # Production quality
        sa.Column("production_quality_score", sa.Integer, nullable=True),  # 1-10
        sa.Column("text_to_image_ratio", sa.Numeric(5, 2), nullable=True),  # percentage
        # Visual analysis
        sa.Column(
            "color_palette", postgresql.JSONB, nullable=True
        ),  # ["#FF5733", "#C70039", "#900C3F"]
        sa.Column("has_human_face", sa.Boolean, nullable=True),
        sa.Column("has_product_shot", sa.Boolean, nullable=True),
        # Metadata
        sa.Column("analysis_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("model_used", sa.String(100), nullable=True),
    )
    op.create_index("idx_ad_creative_analysis_ad_id", "ad_creative_analysis", ["ad_id"])
    op.create_index(
        "idx_ad_creative_analysis_archetype", "ad_creative_analysis", ["creative_archetype"]
    )
    op.create_index(
        "idx_ad_creative_analysis_hook_offer", "ad_creative_analysis", ["hook_offer_type"]
    )

    # Create cross_platform_ads table
    op.create_table(
        "cross_platform_ads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("domain", sa.String(255), nullable=False),  # Advertiser's website domain
        sa.Column("platform", sa.String(50), nullable=False),  # facebook, tiktok, google
        sa.Column("platform_ad_id", sa.String(255), nullable=True),  # Ad ID on that platform
        sa.Column("platform_ad_url", sa.Text, nullable=True),  # URL to view the ad
        sa.Column("creative_hash", sa.String(64), nullable=True),  # Perceptual hash for matching
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'")),  # active, inactive
        sa.Column(
            "is_universal_winner", sa.Boolean, server_default=sa.text("false")
        ),  # Found on 3+ platforms
        # Link to our ads table if from Facebook
        sa.Column(
            "ad_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ads.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("idx_cross_platform_ads_domain", "cross_platform_ads", ["domain"])
    op.create_index("idx_cross_platform_ads_platform", "cross_platform_ads", ["platform"])
    op.create_index("idx_cross_platform_ads_creative_hash", "cross_platform_ads", ["creative_hash"])
    op.create_index(
        "idx_cross_platform_ads_universal_winner", "cross_platform_ads", ["is_universal_winner"]
    )

    # Update ads table with new columns
    op.add_column("ads", sa.Column("landing_page_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ads", sa.Column("landing_page_url", sa.Text, nullable=True))
    op.add_column("ads", sa.Column("is_carousel", sa.Boolean, server_default=sa.text("false")))
    op.add_column("ads", sa.Column("carousel_item_count", sa.Integer, nullable=True))
    op.add_column(
        "ads", sa.Column("carousel_items", postgresql.JSONB, nullable=True)
    )  # [{url: "", type: "image/video"}]
    op.add_column(
        "ads", sa.Column("ad_delivery_stop_time", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("ads", sa.Column("last_seen_active", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ads", sa.Column("is_active", sa.Boolean, server_default=sa.text("true")))

    # Add foreign key for landing_page_id
    op.create_foreign_key(
        "fk_ads_landing_page_id",
        "ads",
        "landing_pages",
        ["landing_page_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_ads_landing_page_id", "ads", ["landing_page_id"])
    op.create_index("idx_ads_is_active", "ads", ["is_active"])


def downgrade() -> None:
    # Remove indexes and foreign key from ads
    op.drop_index("idx_ads_is_active", table_name="ads")
    op.drop_index("idx_ads_landing_page_id", table_name="ads")
    op.drop_constraint("fk_ads_landing_page_id", "ads", type_="foreignkey")

    # Remove new columns from ads
    op.drop_column("ads", "is_active")
    op.drop_column("ads", "last_seen_active")
    op.drop_column("ads", "ad_delivery_stop_time")
    op.drop_column("ads", "carousel_items")
    op.drop_column("ads", "carousel_item_count")
    op.drop_column("ads", "is_carousel")
    op.drop_column("ads", "landing_page_url")
    op.drop_column("ads", "landing_page_id")

    # Drop cross_platform_ads table
    op.drop_index("idx_cross_platform_ads_universal_winner", table_name="cross_platform_ads")
    op.drop_index("idx_cross_platform_ads_creative_hash", table_name="cross_platform_ads")
    op.drop_index("idx_cross_platform_ads_platform", table_name="cross_platform_ads")
    op.drop_index("idx_cross_platform_ads_domain", table_name="cross_platform_ads")
    op.drop_table("cross_platform_ads")

    # Drop ad_creative_analysis table
    op.drop_index("idx_ad_creative_analysis_hook_offer", table_name="ad_creative_analysis")
    op.drop_index("idx_ad_creative_analysis_archetype", table_name="ad_creative_analysis")
    op.drop_index("idx_ad_creative_analysis_ad_id", table_name="ad_creative_analysis")
    op.drop_table("ad_creative_analysis")

    # Drop landing_pages table
    op.drop_index("idx_landing_pages_meta_pixel_id", table_name="landing_pages")
    op.drop_index("idx_landing_pages_url_hash", table_name="landing_pages")
    op.drop_table("landing_pages")
