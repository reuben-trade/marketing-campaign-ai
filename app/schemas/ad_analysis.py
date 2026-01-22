"""Enhanced ad analysis schemas for cinematic and rhetorical analysis."""

from pydantic import BaseModel, Field


class CinematicDetails(BaseModel):
    """Cinematic properties of a narrative beat."""

    camera_angle: str = Field(
        ...,
        description="e.g., Low-angle, POV, Close-up, Dolly-in, Wide-shot, Over-the-shoulder",
    )
    lighting_style: str = Field(
        ...,
        description="e.g., High-contrast, Natural/UGC, Studio-soft, Golden-hour, Ring-light",
    )
    cinematic_features: list[str] = Field(
        ...,
        description="e.g., ['Slow-mo', 'Rapid-cuts', 'Text-overlay', 'Split-screen', 'B-roll']",
    )


class RhetoricalAppeal(BaseModel):
    """Rhetorical appeal analysis for a narrative beat."""

    mode: str = Field(
        ...,
        description="Logos (logic/facts), Pathos (emotion), Ethos (credibility), or Kairos (urgency/timing)",
    )
    description: str = Field(
        ...,
        description="How the appeal is executed in this specific beat - be detailed and specific",
    )


class NarrativeBeat(BaseModel):
    """A natural segment of the video based on narrative/cinematic shifts."""

    start_time: str = Field(..., description="Start time in MM:SS format")
    end_time: str = Field(..., description="End time in MM:SS format")
    beat_type: str = Field(
        ...,
        description="Hook, Problem, Solution, Social Proof, CTA, Transition, or Feature Demo",
    )
    cinematics: CinematicDetails = Field(
        ...,
        description="Camera work and production style for this beat",
    )
    tone_of_voice: str = Field(
        ...,
        description="e.g., Urgent, Empathetic, ASMR, High-energy, Conversational, Authoritative",
    )
    rhetorical_appeal: RhetoricalAppeal = Field(
        ...,
        description="Primary persuasion technique used in this beat",
    )
    target_audience_cues: str = Field(
        ...,
        description="Visual/audio signals identifying the target demographic (age, lifestyle, pain points)",
    )
    visual_description: str = Field(
        ...,
        description="Detailed visual narration - what is shown, who appears, setting, colors, key elements",
    )
    audio_transcript: str = Field(
        ...,
        description="Exact transcript of spoken words, music description, sound effects",
    )


class EnhancedAdAnalysis(BaseModel):
    """Complete enhanced video analysis with narrative beats and creative DNA."""

    inferred_audience: str = Field(
        ...,
        description="Detailed target audience profile based on all visual and audio cues",
    )
    primary_messaging_pillar: str = Field(
        ...,
        description="Core message theme: e.g., 'Cost Savings', 'Premium Quality', 'Convenience', 'Social Status'",
    )
    overall_pacing_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="1-10 score for pacing effectiveness (rhythm, energy, attention retention)",
    )
    production_style: str = Field(
        ...,
        description="Overall production classification: 'High-production Studio', 'Authentic UGC', 'Hybrid', 'Animation'",
    )
    hook_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="1-10 score for first beat's attention-grabbing effectiveness",
    )
    timeline: list[NarrativeBeat] = Field(
        ...,
        description="Ordered list of natural beats that make up the video narrative",
    )
    overall_narrative_summary: str = Field(
        ...,
        description="2-3 sentence summary that captures the ad's story arc and emotional journey",
    )
