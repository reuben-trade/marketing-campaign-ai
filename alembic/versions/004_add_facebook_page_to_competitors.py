"""Add facebook_page column to competitors table.

Revision ID: 004
Revises: 003
Create Date: 2026-01-20

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add facebook_page column with unique constraint
    op.add_column(
        "competitors",
        sa.Column("facebook_page", sa.String(255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_competitors_facebook_page",
        "competitors",
        ["facebook_page"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_competitors_facebook_page", "competitors", type_="unique")
    op.drop_column("competitors", "facebook_page")
