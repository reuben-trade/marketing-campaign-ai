"""Analysis Run model for logging."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class AnalysisRun(Base):
    """Analysis runs table for logging pipeline executions."""

    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g., "competitor_discovery", "ad_retrieval", "ad_analysis", "recommendation_generation"

    status: Mapped[str] = mapped_column(String(50), default="pending")
    # "pending", "running", "completed", "failed"

    # Metrics
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    parameters: Mapped[dict | None] = mapped_column(JSONB)
    logs: Mapped[dict | None] = mapped_column(JSONB)

    @property
    def duration_seconds(self) -> float | None:
        """Calculate run duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.items_processed + self.items_failed
        if total == 0:
            return 0.0
        return self.items_processed / total * 100
