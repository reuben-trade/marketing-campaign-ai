"""Recommendation model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Recommendation(Base):
    """Recommendations table."""

    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    generated_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Input parameters
    top_n_ads: Mapped[int | None] = mapped_column(Integer)
    date_range_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    date_range_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Output
    trend_analysis: Mapped[dict | None] = mapped_column(JSONB)
    # Structure: {
    #   "visual_trends": list[{
    #     "trend": str,
    #     "prevalence": str,
    #     "description": str,
    #     "why_it_works": str,
    #     "example_ad_ids": list[str]
    #   }],
    #   "messaging_trends": list[{...}],
    #   "cta_trends": list[{...}],
    #   "engagement_patterns": {
    #     "best_performing_length": str,
    #     "optimal_posting_time": str,
    #     "hook_timing": str
    #   }
    # }

    recommendations: Mapped[dict | None] = mapped_column(JSONB)
    # Full structure as defined in section 7 of the spec

    executive_summary: Mapped[str | None] = mapped_column(JSONB)

    implementation_roadmap: Mapped[dict | None] = mapped_column(JSONB)
    # Structure: {
    #   "phase_1_immediate": {...},
    #   "phase_2_support": {...},
    #   "testing_protocol": {...}
    # }

    # Tracking
    ads_analyzed: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    generation_time_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    model_used: Mapped[str | None] = mapped_column(String(100))
