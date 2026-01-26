"""Add agentic ad engine tables.

Creates tables for the MVP ad generation pipeline:
- brand_profiles: User brand context for ad generation
- recipes: Structural templates extracted from high-performing ads
- projects: User ad creation projects
- user_video_segments: Analyzed segments from user uploads
- visual_scripts: Generated ad scripts with slots
- rendered_videos: Video rendering jobs and outputs

Revision ID: 013
Revises: 012
Create Date: 2026-01-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # noqa: F401

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create brand_profiles table
    op.create_table(
        "brand_profiles",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("industry", sa.String(100), nullable=False),
        sa.Column("niche", sa.String(200), nullable=True),
        sa.Column("core_offer", sa.Text(), nullable=True),
        sa.Column("competitors", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("keywords", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("tone", sa.String(50), nullable=True),
        sa.Column("forbidden_terms", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=True),
        sa.Column("font_family", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_brand_profiles_industry", "brand_profiles", ["industry"])
    op.create_index("idx_brand_profiles_created_at", "brand_profiles", ["created_at"])

    # 2. Create recipes table
    op.create_table(
        "recipes",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "source_ad_id",
            sa.Uuid(),
            sa.ForeignKey("ads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("total_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("structure", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("pacing", sa.String(50), nullable=True),
        sa.Column("style", sa.String(50), nullable=True),
        sa.Column("composite_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_recipes_source_ad_id", "recipes", ["source_ad_id"])
    op.create_index("idx_recipes_composite_score", "recipes", ["composite_score"])
    op.create_index("idx_recipes_style", "recipes", ["style"])
    op.create_index("idx_recipes_pacing", "recipes", ["pacing"])
    op.create_index("idx_recipes_created_at", "recipes", ["created_at"])

    # 3. Create projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "brand_profile_id",
            sa.Uuid(),
            sa.ForeignKey("brand_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(50), server_default="draft", nullable=False),
        sa.Column("inspiration_ads", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("user_prompt", sa.Text(), nullable=True),
        sa.Column("max_videos", sa.Integer(), server_default="10", nullable=False),
        sa.Column("max_total_size_mb", sa.Integer(), server_default="500", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_projects_brand_profile_id", "projects", ["brand_profile_id"])
    op.create_index("idx_projects_status", "projects", ["status"])
    op.create_index("idx_projects_created_at", "projects", ["created_at"])

    # 4. Create user_video_segments table
    op.create_table(
        "user_video_segments",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_file_id", sa.Uuid(), nullable=False),
        sa.Column("source_file_name", sa.String(500), nullable=True),
        sa.Column("source_file_url", sa.Text(), nullable=True),
        sa.Column("timestamp_start", sa.Float(), nullable=False),
        sa.Column("timestamp_end", sa.Float(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("visual_description", sa.Text(), nullable=True),
        sa.Column("action_tags", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_user_video_segments_project_id", "user_video_segments", ["project_id"])
    op.create_index("idx_user_video_segments_source_file_id", "user_video_segments", ["source_file_id"])
    op.create_index("idx_user_video_segments_created_at", "user_video_segments", ["created_at"])

    # Create HNSW index for user_video_segments embedding similarity search
    op.execute(
        """
        CREATE INDEX user_video_segments_embedding_hnsw_idx
        ON user_video_segments
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """
    )

    # 5. Create visual_scripts table
    op.create_table(
        "visual_scripts",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recipe_id",
            sa.Uuid(),
            sa.ForeignKey("recipes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("total_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("slots", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("audio_suggestion", sa.String(100), nullable=True),
        sa.Column("pacing_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_visual_scripts_project_id", "visual_scripts", ["project_id"])
    op.create_index("idx_visual_scripts_recipe_id", "visual_scripts", ["recipe_id"])
    op.create_index("idx_visual_scripts_created_at", "visual_scripts", ["created_at"])

    # 6. Create rendered_videos table
    op.create_table(
        "rendered_videos",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("composition_id", sa.String(100), nullable=True),
        sa.Column("remotion_payload", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("render_time_seconds", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_rendered_videos_project_id", "rendered_videos", ["project_id"])
    op.create_index("idx_rendered_videos_status", "rendered_videos", ["status"])
    op.create_index("idx_rendered_videos_created_at", "rendered_videos", ["created_at"])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)

    # 6. Drop rendered_videos
    op.drop_index("idx_rendered_videos_created_at", "rendered_videos")
    op.drop_index("idx_rendered_videos_status", "rendered_videos")
    op.drop_index("idx_rendered_videos_project_id", "rendered_videos")
    op.drop_table("rendered_videos")

    # 5. Drop visual_scripts
    op.drop_index("idx_visual_scripts_created_at", "visual_scripts")
    op.drop_index("idx_visual_scripts_recipe_id", "visual_scripts")
    op.drop_index("idx_visual_scripts_project_id", "visual_scripts")
    op.drop_table("visual_scripts")

    # 4. Drop user_video_segments
    op.drop_index("user_video_segments_embedding_hnsw_idx", "user_video_segments")
    op.drop_index("idx_user_video_segments_created_at", "user_video_segments")
    op.drop_index("idx_user_video_segments_source_file_id", "user_video_segments")
    op.drop_index("idx_user_video_segments_project_id", "user_video_segments")
    op.drop_table("user_video_segments")

    # 3. Drop projects
    op.drop_index("idx_projects_created_at", "projects")
    op.drop_index("idx_projects_status", "projects")
    op.drop_index("idx_projects_brand_profile_id", "projects")
    op.drop_table("projects")

    # 2. Drop recipes
    op.drop_index("idx_recipes_created_at", "recipes")
    op.drop_index("idx_recipes_pacing", "recipes")
    op.drop_index("idx_recipes_style", "recipes")
    op.drop_index("idx_recipes_composite_score", "recipes")
    op.drop_index("idx_recipes_source_ad_id", "recipes")
    op.drop_table("recipes")

    # 1. Drop brand_profiles
    op.drop_index("idx_brand_profiles_created_at", "brand_profiles")
    op.drop_index("idx_brand_profiles_industry", "brand_profiles")
    op.drop_table("brand_profiles")
