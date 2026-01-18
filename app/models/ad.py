"""Ad model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Ad(Base):
    """Ads table."""

    __tablename__ = "ads"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Meta Ad Library identifiers
    ad_library_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ad_snapshot_url: Mapped[str | None] = mapped_column(Text)

    # Creative content
    creative_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # "image" or "video"

    creative_storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    # Supabase Storage path

    creative_url: Mapped[str | None] = mapped_column(Text)
    # Original Meta CDN URL (backup)

    # Ad content
    ad_copy: Mapped[str | None] = mapped_column(Text)
    ad_headline: Mapped[str | None] = mapped_column(Text)
    ad_description: Mapped[str | None] = mapped_column(Text)
    cta_text: Mapped[str | None] = mapped_column(String(255))

    # Engagement metrics
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int | None] = mapped_column(Integer)

    # Analysis results
    analysis: Mapped[dict | None] = mapped_column(JSON)
    # Structure: {
    #   "summary": str,
    #   "insights": list[str],
    #   "uvps": list[str],
    #   "ctas": list[str],
    #   "visual_themes": list[str],
    #   "target_audience": str,
    #   "emotional_appeal": str,
    #   "marketing_effectiveness": {
    #     "hook_strength": int (1-10),
    #     "message_clarity": int (1-10),
    #     "visual_impact": int (1-10),
    #     "cta_effectiveness": int (1-10),
    #     "overall_score": int (1-10)
    #   },
    #   "strategic_insights": str,
    #   "reasoning": str,
    #   "video_analysis": {  # Only for videos
    #     "pacing": str,
    #     "audio_strategy": str,
    #     "story_arc": str,
    #     "caption_usage": str,
    #     "optimal_length": str
    #   }
    # }

    # Metadata
    publication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    analyzed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status flags
    download_status: Mapped[str] = mapped_column(String(20), default="pending")
    # "pending", "completed", "failed"

    analysis_status: Mapped[str] = mapped_column(String(20), default="pending")
    # "pending", "completed", "failed"

    # Relationships
    competitor: Mapped["Competitor"] = relationship(  # noqa: F821
        "Competitor",
        back_populates="ads",
    )

    __table_args__ = (
        Index("idx_ads_competitor", "competitor_id"),
        Index("idx_ads_analyzed", "analyzed"),
        Index("idx_ads_creative_type", "creative_type"),
        Index("idx_ads_publication_date", "publication_date", postgresql_ops={"publication_date": "DESC"}),
    )

    @property
    def total_engagement(self) -> int:
        """Calculate total engagement."""
        return self.likes + self.comments + self.shares

    @property
    def overall_score(self) -> float | None:
        """Get overall marketing effectiveness score from analysis."""
        if self.analysis and "marketing_effectiveness" in self.analysis:
            return self.analysis["marketing_effectiveness"].get("overall_score")
        return None
