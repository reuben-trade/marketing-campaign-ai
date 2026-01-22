"""Recommendation schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class VisualTrend(BaseModel):
    """Visual trend analysis."""

    trend: str
    prevalence: str
    description: str
    why_it_works: str
    example_ad_ids: list[str] = Field(default_factory=list)


class MessagingTrend(BaseModel):
    """Messaging trend analysis."""

    trend: str
    prevalence: str
    description: str
    why_it_works: str
    example_ad_ids: list[str] = Field(default_factory=list)


class CTATrend(BaseModel):
    """CTA trend analysis."""

    trend: str
    examples: list[str]
    effectiveness: str


class EngagementPatterns(BaseModel):
    """Engagement pattern analysis."""

    best_performing_length: str
    optimal_posting_time: str
    hook_timing: str


class TrendAnalysis(BaseModel):
    """Complete trend analysis."""

    visual_trends: list[VisualTrend] = Field(default_factory=list)
    messaging_trends: list[MessagingTrend] = Field(default_factory=list)
    cta_trends: list[CTATrend] = Field(default_factory=list)
    engagement_patterns: EngagementPatterns | None = None


class ColorPalette(BaseModel):
    """Color palette for visual direction."""

    primary: str
    secondary: str
    accent: str
    reasoning: str | None = None
    background: str | None = None
    text: str | None = None


class VisualDirection(BaseModel):
    """Visual direction for an ad recommendation."""

    overall_style: str | None = None
    setting: str | None = None
    color_palette: ColorPalette | None = None
    composition: str | None = None
    camera_work: str | None = None
    layout: str | None = None
    style: str | None = None


class ScriptSection(BaseModel):
    """A section of the video script."""

    timing: str
    visual_description: str
    action: str | None = None
    audio: str | None = None
    voiceover: str | None = None
    on_screen_text: str
    text_style: str
    why_this_works: str | None = None
    product_demo: str | None = None
    text_overlay: str | None = None
    urgency_element: str | None = None


class ScriptBreakdown(BaseModel):
    """Full script breakdown for video ads."""

    hook: ScriptSection | None = None
    problem_agitation: ScriptSection | None = None
    solution_introduction: ScriptSection | None = None
    social_proof: ScriptSection | None = None
    cta: ScriptSection | None = None


class CaptionStrategy(BaseModel):
    """Caption strategy for video ads."""

    necessity: str
    font: str
    size: str
    placement: str
    timing: str
    animations: str
    emoji_usage: str
    background: str


class ShotRequirement(BaseModel):
    """Individual shot requirement."""

    shot_type: str
    description: str
    duration: str
    purpose: str


class FilmingRequirements(BaseModel):
    """Filming requirements for video ads."""

    shots_needed: list[ShotRequirement] = Field(default_factory=list)
    b_roll: list[str] = Field(default_factory=list)
    talent: str | None = None
    props: str | None = None


class MusicSpec(BaseModel):
    """Music specification."""

    style: str
    tempo: str
    energy: str
    when: str
    reference: str | None = None


class VoiceoverSpec(BaseModel):
    """Voiceover specification."""

    tone: str
    gender: str
    pace: str
    emphasis: str


class AudioDesign(BaseModel):
    """Audio design for video ads."""

    music: MusicSpec | None = None
    sound_effects: list[str] = Field(default_factory=list)
    voiceover: VoiceoverSpec | None = None


class ContentSection(BaseModel):
    """Content section for image ads."""

    visual: str
    text: str
    style: str


class ContentBreakdown(BaseModel):
    """Content breakdown for image ads."""

    left_side_problem: ContentSection | None = None
    right_side_solution: ContentSection | None = None
    center_divider: str | None = None


class CopyElement(BaseModel):
    """Copywriting element."""

    text: str
    placement: str
    font: str | None = None
    color: str | None = None
    size: str | None = None
    style: str | None = None


class Copywriting(BaseModel):
    """Copywriting for image ads."""

    headline: CopyElement | None = None
    subheadline: CopyElement | None = None
    body_copy: CopyElement | None = None
    cta_button: CopyElement | None = None


class DesignSpecifications(BaseModel):
    """Design specifications for image ads."""

    dimensions: str
    file_format: str
    file_size: str
    safe_zones: str
    text_coverage: str
    contrast_ratio: str
    mobile_optimization: str


class TestingVariant(BaseModel):
    """A/B testing variant."""

    variable: str
    variant_a: str
    variant_b: str
    hypothesis: str


class TargetingAlignment(BaseModel):
    """Targeting alignment details."""

    audience: str
    pain_point_addressed: str
    brand_voice_alignment: str
    price_point_justification: str


class SuccessMetrics(BaseModel):
    """Success metrics for recommendations."""

    primary: str
    secondary: list[str] = Field(default_factory=list)
    optimization: str


class ProductionNotes(BaseModel):
    """Production notes for image ads."""

    tools: str
    assets_needed: list[str] = Field(default_factory=list)
    time_estimate: str


class RecommendationConcept(BaseModel):
    """Recommendation concept."""

    title: str
    description: str
    marketing_framework: str | None = None


class AdRecommendation(BaseModel):
    """Single ad recommendation."""

    recommendation_id: int
    priority: str = Field(..., pattern="^(high|medium|low)$")
    ad_format: str = Field(..., pattern="^(video|image)$")
    duration: str | None = None
    objective: str

    concept: RecommendationConcept
    visual_direction: VisualDirection | None = None

    # Video-specific
    script_breakdown: ScriptBreakdown | None = None
    caption_strategy: CaptionStrategy | None = None
    filming_requirements: FilmingRequirements | None = None
    audio_design: AudioDesign | None = None

    # Image-specific
    content_breakdown: ContentBreakdown | None = None
    copywriting: Copywriting | None = None
    design_specifications: DesignSpecifications | None = None
    production_notes: ProductionNotes | None = None

    # Common
    targeting_alignment: TargetingAlignment | None = None
    testing_variants: list[TestingVariant] = Field(default_factory=list)
    success_metrics: SuccessMetrics | None = None


class ImplementationPhase(BaseModel):
    """Implementation phase details."""

    action: str
    rationale: str
    timeline: str
    budget_allocation: str


class TestingProtocol(BaseModel):
    """Testing protocol details."""

    duration: str
    kpis: list[str]
    decision_criteria: str


class ImplementationRoadmap(BaseModel):
    """Implementation roadmap."""

    phase_1_immediate: ImplementationPhase | None = None
    phase_2_support: ImplementationPhase | None = None
    testing_protocol: TestingProtocol | None = None


class RecommendationCreate(BaseModel):
    """Request to generate recommendations."""

    top_n_ads: int = Field(default=10, ge=1, le=50)
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    focus_areas: list[str] | None = Field(
        None,
        description="Specific areas to focus on (e.g., 'video', 'engagement', 'brand_awareness')",
    )


class RecommendationResponse(BaseModel):
    """Complete recommendation response."""

    id: UUID
    generated_date: datetime
    executive_summary: str | None = None
    trend_analysis: TrendAnalysis | None = None
    recommendations: list[AdRecommendation] = Field(default_factory=list)
    implementation_roadmap: ImplementationRoadmap | None = None
    ads_analyzed: list[UUID] = Field(default_factory=list)
    generation_time_seconds: Decimal | None = None
    model_used: str | None = None

    model_config = {"from_attributes": True}


class RecommendationListResponse(BaseModel):
    """Schema for listing recommendations."""

    items: list[RecommendationResponse]
    total: int
    page: int
    page_size: int
