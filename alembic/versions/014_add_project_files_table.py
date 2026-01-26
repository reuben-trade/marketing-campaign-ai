"""Add project_files table for tracking uploaded videos.

Creates project_files table to track individual video files uploaded to a project.
This enables proper tracking of upload progress, file sizes, and processing status.

Revision ID: 014
Revises: 013
Create Date: 2026-01-26

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create project_files table
    op.create_table(
        "project_files",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_project_files_project_id", "project_files", ["project_id"])
    op.create_index("idx_project_files_status", "project_files", ["status"])
    op.create_index("idx_project_files_created_at", "project_files", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_project_files_created_at", "project_files")
    op.drop_index("idx_project_files_status", "project_files")
    op.drop_index("idx_project_files_project_id", "project_files")
    op.drop_table("project_files")
