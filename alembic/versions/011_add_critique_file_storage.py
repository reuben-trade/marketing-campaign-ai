"""Add file storage fields to critiques table.

Revision ID: 011
Revises: 010
Create Date: 2026-01-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add file storage path and URL columns
    op.add_column(
        "critiques",
        sa.Column("file_storage_path", sa.String(1000), nullable=True),
    )
    op.add_column(
        "critiques",
        sa.Column("file_url", sa.String(2000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("critiques", "file_url")
    op.drop_column("critiques", "file_storage_path")
