"""Add generated_broll tables for Veo 2 B-Roll generation.

Creates generated_broll and generated_broll_clips tables to track AI-generated
video clips using Veo 2.

Revision ID: 015
Revises: 014
Create Date: 2026-01-27

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create generated_broll table (parent table for generation jobs)
    op.create_table(
        "generated_broll",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        # Generation parameters
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("aspect_ratio", sa.String(10), nullable=False),
        sa.Column("style", sa.String(50), nullable=False),
        sa.Column("num_variants", sa.Integer(), server_default="2", nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("seed", sa.Integer(), nullable=True),
        # Optional project/slot association
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("slot_id", sa.String(100), nullable=True),
        # Status tracking
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generation_time_seconds", sa.Float(), nullable=True),
    )
    op.create_index("idx_generated_broll_project_id", "generated_broll", ["project_id"])
    op.create_index("idx_generated_broll_status", "generated_broll", ["status"])
    op.create_index("idx_generated_broll_created_at", "generated_broll", ["created_at"])
    op.create_index("idx_generated_broll_slot_id", "generated_broll", ["slot_id"])

    # Create generated_broll_clips table (individual clip variants)
    op.create_table(
        "generated_broll_clips",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "generation_id",
            sa.Uuid(),
            sa.ForeignKey("generated_broll.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Video metadata
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        # Variant index
        sa.Column("variant_index", sa.Integer(), server_default="0", nullable=False),
        # Timestamp
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_generated_broll_clips_generation_id",
        "generated_broll_clips",
        ["generation_id"],
    )


def downgrade() -> None:
    # Drop clips table first (has FK to parent)
    op.drop_index("idx_generated_broll_clips_generation_id", "generated_broll_clips")
    op.drop_table("generated_broll_clips")

    # Drop parent table
    op.drop_index("idx_generated_broll_slot_id", "generated_broll")
    op.drop_index("idx_generated_broll_created_at", "generated_broll")
    op.drop_index("idx_generated_broll_status", "generated_broll")
    op.drop_index("idx_generated_broll_project_id", "generated_broll")
    op.drop_table("generated_broll")
