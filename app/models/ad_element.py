"""Ad element model for storing narrative beats/timeline elements."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AdElement(Base):
    """Ad elements table - stores individual narrative beats from video analysis timeline."""

    __tablename__ = "ad_elements"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    ad_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ads.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Position and type
    beat_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # Position in timeline (0, 1, 2...)
    beat_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Values: "Hook", "Problem", "Solution", "Product Showcase", "Social Proof",
    #         "Benefit Stack", "Objection Handling", "CTA", "Transition", "Unknown"

    # Timing
    start_time: Mapped[str | None] = mapped_column(String(10))  # MM:SS format
    end_time: Mapped[str | None] = mapped_column(String(10))  # MM:SS format
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Content
    visual_description: Mapped[str | None] = mapped_column(Text)
    audio_transcript: Mapped[str | None] = mapped_column(Text)
    tone_of_voice: Mapped[str | None] = mapped_column(String(100))

    # Emotion
    emotion: Mapped[str | None] = mapped_column(String(50))
    emotion_intensity: Mapped[int | None] = mapped_column(Integer)  # 1-10
    attention_score: Mapped[int | None] = mapped_column(Integer)  # 1-10

    # Rhetorical analysis
    rhetorical_mode: Mapped[str | None] = mapped_column(String(20))
    # Values: "Logos", "Pathos", "Ethos", "Kairos", "Unknown"
    rhetorical_description: Mapped[str | None] = mapped_column(Text)
    persuasion_techniques: Mapped[list | None] = mapped_column(JSON)
    # e.g., ["scarcity", "social proof", "authority"]

    # Cinematics
    camera_angle: Mapped[str | None] = mapped_column(String(50))
    lighting_style: Mapped[str | None] = mapped_column(String(50))
    color_grading: Mapped[str | None] = mapped_column(String(50))
    motion_type: Mapped[str | None] = mapped_column(String(50))
    transition_in: Mapped[str | None] = mapped_column(String(50))
    transition_out: Mapped[str | None] = mapped_column(String(50))
    cinematic_features: Mapped[list | None] = mapped_column(JSON)
    # e.g., ["Slow-mo", "Text-overlay", "Split-screen"]

    # Visual elements
    text_overlays: Mapped[list | None] = mapped_column(JSON)
    # Array of TextOverlay objects
    key_visual_elements: Mapped[list | None] = mapped_column(JSON)
    # e.g., ["product", "face", "hands", "lifestyle shot"]
    target_audience_cues: Mapped[str | None] = mapped_column(Text)

    # Improvement suggestions
    improvement_note: Mapped[str | None] = mapped_column(Text)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    ad: Mapped["Ad"] = relationship(  # noqa: F821
        "Ad",
        back_populates="elements",
    )

    __table_args__ = (
        Index("idx_ad_elements_ad_id", "ad_id"),
        Index("idx_ad_elements_beat_type", "beat_type"),
        Index("idx_ad_elements_ad_beat", "ad_id", "beat_index"),
        Index("idx_ad_elements_emotion", "emotion"),
        Index("idx_ad_elements_rhetorical_mode", "rhetorical_mode"),
        Index("idx_ad_elements_attention_score", "attention_score"),
    )

    # Valid beat types
    BEAT_TYPES = [
        "Hook",
        "Problem",
        "Solution",
        "Product Showcase",
        "Social Proof",
        "Benefit Stack",
        "Objection Handling",
        "CTA",
        "Transition",
        "Unknown",
    ]

    # Valid rhetorical modes
    RHETORICAL_MODES = [
        "Logos",
        "Pathos",
        "Ethos",
        "Kairos",
        "Unknown",
    ]
