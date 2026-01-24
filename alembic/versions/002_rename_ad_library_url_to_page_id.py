"""Rename ad_library_url to page_id.

Revision ID: 002
Revises: 001
Create Date: 2026-01-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, extract page_id from existing URLs
    # URLs are in format: https://www.facebook.com/ads/library/?view_all_page_id=123456789
    # We need to extract just the page ID number
    op.execute("""
        UPDATE competitors
        SET ad_library_url = COALESCE(
            -- Try to extract view_all_page_id parameter
            SUBSTRING(ad_library_url FROM 'view_all_page_id=([0-9]+)'),
            -- Try to extract id parameter
            SUBSTRING(ad_library_url FROM '[?&]id=([0-9]+)'),
            -- If it's already just a number, keep it
            CASE WHEN ad_library_url ~ '^[0-9]+$' THEN ad_library_url ELSE NULL END,
            -- Fallback: keep original (will fail if too long, but that's expected)
            ad_library_url
        )
    """)

    # Now rename and change type
    op.alter_column(
        "competitors",
        "ad_library_url",
        new_column_name="page_id",
        type_=sa.String(50),
        existing_type=sa.Text,
        existing_nullable=False,
    )


def downgrade() -> None:
    # Rename column back from page_id to ad_library_url
    op.alter_column(
        "competitors",
        "page_id",
        new_column_name="ad_library_url",
        type_=sa.Text,
        existing_type=sa.String(50),
        existing_nullable=False,
    )

    # Rebuild full URLs from page_id
    op.execute("""
        UPDATE competitors
        SET ad_library_url = 'https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id=' || ad_library_url
        WHERE ad_library_url ~ '^[0-9]+$'
    """)
