"""Critique model for persisted user ad feedback."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Critique(Base):
    """Critiques table - persists user ad feedback results."""

    __tablename__ = "critiques"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # File info
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_storage_path: Mapped[str | None] = mapped_column(String(1000))
    file_url: Mapped[str | None] = mapped_column(String(2000))

    # User-provided context
    brand_name: Mapped[str | None] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(255))
    target_audience: Mapped[str | None] = mapped_column(Text)
    platform_cta: Mapped[str | None] = mapped_column(String(255))

    # Full analysis (EnhancedAdAnalysisV2 as JSONB)
    analysis: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Denormalized scores for listing/filtering
    overall_grade: Mapped[str | None] = mapped_column(String(5))
    hook_score: Mapped[int | None] = mapped_column(Integer)
    pacing_score: Mapped[int | None] = mapped_column(Integer)
    thumb_stop_score: Mapped[int | None] = mapped_column(Integer)
    analysis_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))

    # Processing metadata
    model_used: Mapped[str | None] = mapped_column(String(100))
    processing_time_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
