"""Add notifications table.

Revision ID: 009
Revises: 008
Create Date: 2026-01-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column(
            "competitor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("competitors.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "ad_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ad_count", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index(
        "idx_notifications_created_at",
        "notifications",
        ["created_at"],
    )
    op.create_index(
        "idx_notifications_read_at",
        "notifications",
        ["read_at"],
    )
    op.create_index(
        "idx_notifications_type",
        "notifications",
        ["type"],
    )


def downgrade() -> None:
    op.drop_index("idx_notifications_type")
    op.drop_index("idx_notifications_read_at")
    op.drop_index("idx_notifications_created_at")
    op.drop_table("notifications")
