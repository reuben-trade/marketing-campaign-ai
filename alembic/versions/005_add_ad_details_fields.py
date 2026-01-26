"""Add detailed ad fields for modal scraping.

Revision ID: 005
Revises: 004
Create Date: 2026-01-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for detailed ad information from modal view
    op.add_column(
        "ads",
        sa.Column("started_running_date", sa.Date, nullable=True),
    )
    op.add_column(
        "ads",
        sa.Column("total_active_time", sa.String(100), nullable=True),
    )
    op.add_column(
        "ads",
        sa.Column("platforms", postgresql.ARRAY(sa.String), nullable=True),
    )
    op.add_column(
        "ads",
        sa.Column("link_headline", sa.Text, nullable=True),
    )
    op.add_column(
        "ads",
        sa.Column("link_description", sa.Text, nullable=True),
    )
    op.add_column(
        "ads",
        sa.Column("additional_links", postgresql.ARRAY(sa.Text), nullable=True),
    )
    op.add_column(
        "ads",
        sa.Column("form_fields", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ads", "form_fields")
    op.drop_column("ads", "additional_links")
    op.drop_column("ads", "link_description")
    op.drop_column("ads", "link_headline")
    op.drop_column("ads", "platforms")
    op.drop_column("ads", "total_active_time")
    op.drop_column("ads", "started_running_date")
