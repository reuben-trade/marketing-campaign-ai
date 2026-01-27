"""Enhanced ad analysis schemas for cinematic and rhetorical analysis."""

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

RhetoricalMode = Literal["Logos", "Pathos", "Ethos", "Kairos", "Unknown"]

# EmotionType is now a plain string to allow any emotion the LLM returns
EmotionType = str

# AdComponentType: Strict ad component types for structural analysis
# These are the key components that should be identified in every ad
AdComponentType = Literal[
    "Hook",  # The first 0-5s attention grabber
    "Problem",  # Agitating the pain point
    "Solution",  # The "Product Reveal" moment
    "Product Showcase",  # Demoing features/how it works
    "Social Proof",  # Testimonials, reviews, UGC
    "Benefit Stack",  # Listing value propositions
    "Objection Handling",  # Addressing doubts/trust markers
    "CTA",  # Call to Action
    "Transition",  # Visual bridge between sections
]

# BeatType: Extended type that includes Unknown for backwards compatibility
BeatType = Literal[
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

ProductionStyleType = Literal[
    "High-production Studio",
    "Authentic UGC",
    "Hybrid",
    "Animation",
    "Stock Footage Mashup",
    "Screen Recording",
    "Talking Head",
    "Documentary Style",
    "Influencer Native",
    "Unknown",
]

AspectRatioType = Literal["9:16", "16:9", "1:1", "4:5", "4:3", "2.35:1", "Unknown"]

CopyFrameworkType = Literal[
    "PAS",  # Problem-Agitation-Solution
    "AIDA",  # Attention-Interest-Desire-Action
    "BAB",  # Before-After-Bridge
    "FAB",  # Features-Advantages-Benefits
    "4Ps",  # Promise-Picture-Proof-Push
    "QUEST",  # Qualify-Understand-Educate-Stimulate-Transition
    "PASTOR",  # Problem-Amplify-Story-Testimony-Offer-Response
    "SLAP",  # Stop-Look-Act-Purchase
    "STAR",  # Situation-Task-Action-Result
    "Custom",
    "Unknown",
]


# =============================================================================
# ORIGINAL V1 MODELS (preserved for backward compatibility)
# =============================================================================


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
        default_factory=list,
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
    """Complete enhanced video analysis with narrative beats and creative DNA (V1)."""

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
        default_factory=list,
        description="Ordered list of natural beats that make up the video narrative",
    )
    overall_narrative_summary: str = Field(
        ...,
        description="2-3 sentence summary that captures the ad's story arc and emotional journey",
    )


# =============================================================================
# V2 MODELS - TEXT/COPY ANALYSIS
# =============================================================================


class TextOverlay(BaseModel):
    """Individual text overlay extracted from the ad."""

    text: str = Field(..., description="Exact text content verbatim")
    timestamp: str = Field(
        default="00:00",
        description="When this text appears (MM:SS format) - for video only",
    )
    duration_seconds: float = Field(
        default=0,
        ge=0,
        description="How long the text is visible - for video only",
    )
    position: str = Field(
        default="center",
        description="Screen position: top, center, bottom, lower-third, full-screen",
    )
    typography: str | None = Field(
        None,
        description="Font style: bold sans-serif, handwritten, serif, kinetic typography",
    )
    animation: str | None = Field(
        None,
        description="Text animation: fade-in, pop, typewriter, slide, bounce, none",
    )
    emphasis_type: str | None = Field(
        None,
        description="Visual emphasis: highlighted word, underline, color change, size increase",
    )
    purpose: str | None = Field(
        None,
        description="Inferred purpose: hook, benefit statement, stat, testimonial quote, CTA",
    )


class CopyAnalysis(BaseModel):
    """Comprehensive copy/text analysis for the entire ad."""

    all_text_overlays: list[TextOverlay] = Field(
        default_factory=list,
        description="All on-screen text with timestamps - VIDEO ONLY",
    )
    headline_text: str | None = Field(
        None,
        description="Primary headline/hook text if present",
    )
    body_copy: str | None = Field(
        None,
        description="Main body text (for image ads or ad copy)",
    )
    cta_text: str | None = Field(
        None,
        description="Call-to-action text verbatim",
    )
    copy_framework: CopyFrameworkType | None = Field(
        None,
        description="Detected copywriting framework (PAS, AIDA, BAB, etc.)",
    )
    framework_execution: str | None = Field(
        None,
        description="How well the framework is executed - specific details",
    )
    reading_level: str | None = Field(
        None,
        description="Estimated reading level: elementary, middle school, high school, college",
    )
    word_count: int | None = Field(
        None,
        ge=0,
        description="Total word count across all text",
    )
    power_words: list[str] = Field(
        default_factory=list,
        description="Persuasion power words used: free, guaranteed, instant, secret, etc.",
    )
    sensory_words: list[str] = Field(
        default_factory=list,
        description="Sensory/emotional language: feel, imagine, discover, transform",
    )


# =============================================================================
# V2 MODELS - AUDIO ANALYSIS (VIDEO-ONLY)
# =============================================================================


class MusicAnalysis(BaseModel):
    """Detailed music/soundtrack analysis."""

    has_music: bool = Field(default=False, description="Whether background music is present")
    genre: str | None = Field(
        None,
        description="Music genre: electronic, acoustic, hip-hop, cinematic, lo-fi, pop, orchestral",
    )
    tempo: str | None = Field(
        None,
        description="Tempo classification: slow (<80 BPM), medium (80-120), fast (>120), variable",
    )
    energy_level: str | None = Field(
        None,
        description="Energy: calm, building, high-energy, dramatic, uplifting",
    )
    mood: str | None = Field(
        None,
        description="Emotional mood: inspiring, urgent, relaxed, edgy, nostalgic, playful",
    )
    music_sync_moments: list[str] = Field(
        default_factory=list,
        description="Key moments where music syncs with visuals (timestamps)",
    )
    drop_timestamps: list[str] = Field(
        default_factory=list,
        description="Timestamps where music drops/builds for impact",
    )


class VoiceAnalysis(BaseModel):
    """Voice/voiceover characteristics analysis."""

    has_voiceover: bool = Field(default=False, description="Whether voiceover is present")
    has_dialogue: bool = Field(default=False, description="Whether on-screen dialogue is present")
    voice_gender: str | None = Field(
        None,
        description="Perceived gender: male, female, mixed, ambiguous",
    )
    voice_age_range: str | None = Field(
        None,
        description="Perceived age range: young adult (20s), middle-aged (30s-40s), mature (50+)",
    )
    voice_tone: str | None = Field(
        None,
        description="Delivery tone: conversational, authoritative, excited, calm, ASMR, energetic",
    )
    estimated_wpm: int | None = Field(
        None,
        ge=0,
        description="Estimated words per minute (typical range: 120-180)",
    )
    accent: str | None = Field(
        None,
        description="Noticeable accent: American, British, Australian, neutral, regional",
    )


class SoundEffectMarker(BaseModel):
    """Individual sound effect marker."""

    timestamp: str = Field(..., description="When the SFX occurs (MM:SS)")
    sfx_type: str = Field(
        ...,
        description="Type: whoosh, ding, pop, click, notification, impact, swipe",
    )
    purpose: str | None = Field(
        None,
        description="Why used: transition, emphasis, UI feedback, attention grab",
    )


class AudioAnalysis(BaseModel):
    """Comprehensive audio layer analysis - VIDEO ONLY."""

    music: MusicAnalysis = Field(default_factory=MusicAnalysis)
    voice: VoiceAnalysis = Field(default_factory=VoiceAnalysis)
    sound_effects: list[SoundEffectMarker] = Field(
        default_factory=list,
        description="Timestamped sound effect markers",
    )
    audio_visual_sync_score: int | None = Field(
        None,
        ge=1,
        le=10,
        description="How well audio syncs with visual cuts/moments (1-10)",
    )
    silence_moments: list[str] = Field(
        default_factory=list,
        description="Timestamps of intentional silence for impact",
    )
    sound_off_compatible: bool = Field(
        default=False,
        description="Whether the ad works well without sound (relies on captions/text)",
    )


# =============================================================================
# V2 MODELS - BRAND ELEMENTS
# =============================================================================


class LogoAppearance(BaseModel):
    """Individual logo appearance marker."""

    timestamp: str = Field(default="00:00", description="When logo appears (MM:SS)")
    duration_seconds: float = Field(default=0, ge=0, description="How long visible")
    position: str = Field(
        default="corner",
        description="Screen position: corner watermark, center, end card, integrated",
    )
    size: str = Field(
        default="small",
        description="Relative size: small, medium, large, full-screen",
    )
    animation: str | None = Field(
        None,
        description="Logo animation: fade-in, scale-up, reveal, static",
    )


class ProductAppearance(BaseModel):
    """Individual product shot marker."""

    timestamp: str = Field(default="00:00", description="When product appears (MM:SS)")
    duration_seconds: float = Field(default=0, ge=0, description="How long visible")
    shot_type: str = Field(
        default="hero shot",
        description="Type: hero shot, in-use, unboxing, comparison, detail, lifestyle",
    )
    prominence: str = Field(
        default="primary focus",
        description="Prominence: primary focus, background, integrated",
    )
    context: str | None = Field(
        None,
        description="Usage context: hands-on demo, before/after, result showcase",
    )


class BrandElements(BaseModel):
    """Brand presence and consistency analysis."""

    logo_appearances: list[LogoAppearance] = Field(
        default_factory=list,
        description="All logo appearances with timestamps - VIDEO ONLY",
    )
    logo_visible: bool = Field(
        default=False,
        description="Whether logo is visible anywhere in the ad",
    )
    logo_position: str | None = Field(
        None,
        description="Primary logo position for images, or most common for video",
    )
    brand_colors_detected: list[str] = Field(
        default_factory=list,
        description="Hex codes of detected brand colors",
    )
    brand_color_consistency: int | None = Field(
        None,
        ge=1,
        le=10,
        description="How consistently brand colors are used (1-10)",
    )
    product_appearances: list[ProductAppearance] = Field(
        default_factory=list,
        description="All product shots with timestamps - VIDEO ONLY",
    )
    has_product_shot: bool = Field(default=False, description="Whether product is shown")
    product_visibility_seconds: float | None = Field(
        None,
        ge=0,
        description="Total seconds product is visible - VIDEO ONLY",
    )
    brand_mentions_audio: int = Field(
        default=0,
        ge=0,
        description="Number of times brand name is spoken - VIDEO ONLY",
    )
    brand_mentions_text: int = Field(
        default=0,
        ge=0,
        description="Number of times brand name appears in text",
    )


# =============================================================================
# V2 MODELS - ENGAGEMENT PREDICTORS
# =============================================================================


class ThumbStopAnalysis(BaseModel):
    """First-impression scroll-stopping potential analysis."""

    thumb_stop_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Overall scroll-stop potential (1-10)",
    )
    first_frame_hook: str = Field(
        default="",
        description="What makes the first frame attention-grabbing (or why it fails)",
    )
    pattern_interrupt_type: str | None = Field(
        None,
        description="Type of pattern interrupt: unexpected visual, bold text, face, motion, color",
    )
    curiosity_gap: bool = Field(
        default=False,
        description="Whether a curiosity gap is created (incomplete info that demands completion)",
    )
    curiosity_gap_description: str | None = Field(
        None,
        description="How the curiosity gap works or why it's missing",
    )
    first_second_elements: list[str] = Field(
        default_factory=list,
        description="Key visual elements in first second: face, text, product, motion, contrast",
    )
    visual_contrast_score: int | None = Field(
        None,
        ge=1,
        le=10,
        description="Contrast/pop vs feed content (1-10)",
    )
    text_hook_present: bool = Field(
        default=False,
        description="Whether attention-grabbing text appears in first 1-2 seconds",
    )
    face_in_first_frame: bool = Field(
        default=False,
        description="Whether a human face appears in the opening",
    )


class EngagementPredictors(BaseModel):
    """Signals that predict ad engagement and performance."""

    thumb_stop: ThumbStopAnalysis = Field(default_factory=ThumbStopAnalysis)
    scene_change_frequency: float | None = Field(
        None,
        ge=0,
        description="Average seconds between scene changes - VIDEO ONLY",
    )
    visual_variety_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Variety of shots/angles/scenes (1-10)",
    )
    uses_fear_of_missing_out: bool = Field(
        default=False,
        description="Whether FOMO is leveraged",
    )
    uses_social_proof_signals: bool = Field(
        default=False,
        description="Whether social proof elements are present",
    )
    uses_controversy_or_hot_take: bool = Field(
        default=False,
        description="Whether a controversial or bold claim is made",
    )
    uses_transformation_narrative: bool = Field(
        default=False,
        description="Whether before/after transformation is shown",
    )
    predicted_watch_through_rate: str | None = Field(
        None,
        description="Predicted: low (<25%), medium (25-50%), high (>50%) - VIDEO ONLY",
    )
    predicted_engagement_type: str | None = Field(
        None,
        description="Predicted: saves, shares, comments, or clicks",
    )


# =============================================================================
# V2 MODELS - PLATFORM OPTIMIZATION
# =============================================================================


class PlatformOptimization(BaseModel):
    """Platform-specific optimization signals."""

    aspect_ratio: AspectRatioType = Field(
        default="Unknown",
        description="Detected aspect ratio",
    )
    optimal_platforms: list[str] = Field(
        default_factory=list,
        description="Best platforms: instagram_reels, tiktok, facebook_feed, youtube_shorts",
    )
    sound_off_compatible: bool = Field(
        default=False,
        description="Whether ad works without sound",
    )
    caption_dependency: str = Field(
        default="medium",
        description="none, low, medium, high - how much the ad relies on captions",
    )
    native_feel_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="How organic/native it feels vs polished ad (1=very ad-like, 10=very native)",
    )
    native_elements: list[str] = Field(
        default_factory=list,
        description="Elements contributing to native feel: handheld camera, casual tone, etc.",
    )
    duration_seconds: float | None = Field(
        None,
        ge=0,
        description="Total duration in seconds - VIDEO ONLY",
    )
    ideal_duration_assessment: str | None = Field(
        None,
        description="Whether duration is ideal: too short, optimal, too long",
    )
    safe_zone_compliance: bool = Field(
        default=True,
        description="Whether important content stays within safe zones",
    )


# =============================================================================
# V2 MODELS - EMOTIONAL ARC (VIDEO-ONLY)
# =============================================================================


class EmotionalBeatMarker(BaseModel):
    """Emotional state at a specific point in the ad."""

    timestamp: str = Field(..., description="Timestamp (MM:SS)")
    primary_emotion: EmotionType = Field(
        default="neutral", description="Primary emotion at this moment"
    )
    intensity: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Emotional intensity (1-10)",
    )
    trigger: str = Field(
        default="",
        description="What triggers this emotion: visual, audio, story element",
    )


class EmotionalArc(BaseModel):
    """Emotional journey tracking across the ad - VIDEO ONLY."""

    emotional_beats: list[EmotionalBeatMarker] = Field(
        default_factory=list,
        description="Timestamped emotional markers throughout the ad",
    )
    emotional_climax_timestamp: str | None = Field(
        None,
        description="When the emotional peak occurs (MM:SS)",
    )
    tension_build_pattern: str | None = Field(
        None,
        description="How tension builds: gradual, sudden, oscillating, flat",
    )
    resolution_type: str | None = Field(
        None,
        description="How emotional tension resolves: product reveal, transformation, CTA urgency",
    )
    dominant_emotional_tone: EmotionType = Field(
        default="neutral",
        description="Overall emotional tone of the entire ad",
    )


# =============================================================================
# V2 MODELS - ACTIONABLE CRITIQUE
# =============================================================================


class StrengthItem(BaseModel):
    """Individual strength with supporting evidence."""

    strength: str = Field(..., description="What the ad does well")
    evidence: str = Field(..., description="Specific example from the ad")
    timestamp: str | None = Field(
        None,
        description="Timestamp where this strength is demonstrated - VIDEO ONLY",
    )
    impact: str = Field(
        default="",
        description="Why this matters for performance",
    )


class WeaknessItem(BaseModel):
    """Individual weakness with improvement suggestion."""

    weakness: str = Field(..., description="What could be improved")
    evidence: str = Field(..., description="Specific example from the ad")
    timestamp: str | None = Field(
        None,
        description="Timestamp where this weakness appears - VIDEO ONLY",
    )
    impact: str = Field(
        default="",
        description="How this weakness affects performance",
    )
    suggested_fix: str = Field(
        default="",
        description="Actionable improvement suggestion",
    )


class RemakeSuggestion(BaseModel):
    """Detailed suggestion for remaking/improving the ad."""

    section_to_remake: str = Field(
        ...,
        description="Which section: hook, middle, CTA, overall pacing, audio",
    )
    current_approach: str = Field(
        ...,
        description="What the ad currently does",
    )
    suggested_approach: str = Field(
        ...,
        description="Detailed alternative approach",
    )
    expected_improvement: str = Field(
        default="",
        description="What metric this should improve: CTR, watch time, conversions",
    )
    effort_level: str = Field(
        default="moderate edit",
        description="Implementation effort: minor tweak, moderate edit, full reshoot",
    )
    priority: str = Field(
        default="medium",
        description="Priority: high, medium, low",
    )


class AdCritique(BaseModel):
    """Comprehensive critique with actionable feedback."""

    overall_grade: str = Field(
        default="C",
        description="Letter grade: A+, A, A-, B+, B, B-, C+, C, C-, D, F",
    )
    overall_assessment: str = Field(
        default="",
        description="2-3 sentence overall assessment of the ad",
    )
    strengths: list[StrengthItem] = Field(
        default_factory=list,
        description="What the ad does well (3-5 items)",
    )
    weaknesses: list[WeaknessItem] = Field(
        default_factory=list,
        description="What could be improved (3-5 items)",
    )
    remake_suggestions: list[RemakeSuggestion] = Field(
        default_factory=list,
        description="Specific suggestions for improvement (2-4 items)",
    )
    quick_wins: list[str] = Field(
        default_factory=list,
        description="Easy fixes that could be done quickly",
    )
    competitive_position: str | None = Field(
        None,
        description="How this ad compares to industry standards/competitors",
    )


# =============================================================================
# V2 ENHANCED NARRATIVE BEAT (EXTENDS ORIGINAL)
# =============================================================================


class EnhancedCinematicDetails(BaseModel):
    """Extended cinematic properties of a narrative beat."""

    camera_angle: str = Field(
        default="Unknown",
        description="e.g., Low-angle, POV, Close-up, Dolly-in, Wide-shot, Over-the-shoulder",
    )
    lighting_style: str = Field(
        default="Unknown",
        description="e.g., High-contrast, Natural/UGC, Studio-soft, Golden-hour, Ring-light",
    )
    cinematic_features: list[str] = Field(
        default_factory=list,
        description="e.g., ['Slow-mo', 'Rapid-cuts', 'Text-overlay', 'Split-screen', 'B-roll']",
    )
    color_grading: str | None = Field(
        None,
        description="Color treatment: warm, cool, desaturated, high-contrast, vintage, natural",
    )
    motion_type: str | None = Field(
        None,
        description="Camera motion: static, handheld, dolly, pan, zoom, tracking",
    )
    transition_in: str | None = Field(
        None,
        description="How this beat starts: cut, dissolve, wipe, zoom, match-cut",
    )
    transition_out: str | None = Field(
        None,
        description="How this beat ends: cut, dissolve, wipe, zoom, match-cut",
    )


class EnhancedRhetoricalAppeal(BaseModel):
    """Extended rhetorical appeal analysis."""

    mode: RhetoricalMode = Field(
        default="Unknown",
        description="Logos (logic/facts), Pathos (emotion), Ethos (credibility), or Kairos (urgency/timing)",
    )
    description: str = Field(
        default="",
        description="How the appeal is executed in this specific beat",
    )
    secondary_mode: RhetoricalMode | None = Field(
        None,
        description="Secondary persuasion technique if present",
    )
    persuasion_techniques: list[str] = Field(
        default_factory=list,
        description="Specific techniques: scarcity, social proof, authority, reciprocity, consistency",
    )
    objection_addressed: str | None = Field(
        None,
        description="What potential objection this beat addresses, if any",
    )


class EnhancedNarrativeBeat(BaseModel):
    """Extended narrative beat with richer per-segment data."""

    start_time: str = Field(default="00:00", description="Start time in MM:SS format")
    end_time: str = Field(default="00:00", description="End time in MM:SS format")
    beat_type: BeatType = Field(
        default="Unknown",
        description="Hook, Problem, Solution, Social Proof, CTA, Transition, Feature Demo, etc.",
    )
    cinematics: EnhancedCinematicDetails = Field(
        default_factory=EnhancedCinematicDetails,
        description="Camera work and production style for this beat",
    )
    tone_of_voice: str = Field(
        default="",
        description="e.g., Urgent, Empathetic, ASMR, High-energy, Conversational, Authoritative",
    )
    rhetorical_appeal: EnhancedRhetoricalAppeal = Field(
        default_factory=EnhancedRhetoricalAppeal,
        description="Primary persuasion technique used in this beat",
    )
    target_audience_cues: str = Field(
        default="",
        description="Visual/audio signals identifying the target demographic",
    )
    visual_description: str = Field(
        default="",
        description="Detailed visual narration - what is shown, who appears, setting, colors",
    )
    audio_transcript: str = Field(
        default="",
        description="Exact transcript of spoken words, music description, sound effects",
    )
    emotion: EmotionType | None = Field(
        None,
        description="Primary emotion evoked in this beat",
    )
    emotion_intensity: int | None = Field(
        None,
        ge=1,
        le=10,
        description="Intensity of emotion (1-10)",
    )
    text_overlays_in_beat: list[TextOverlay] = Field(
        default_factory=list,
        description="Text overlays that appear during this beat",
    )
    key_visual_elements: list[str] = Field(
        default_factory=list,
        description="Key elements: product, face, hands, lifestyle shot, graphic, animation",
    )
    attention_score: int | None = Field(
        None,
        ge=1,
        le=10,
        description="Predicted attention/engagement for this beat (1-10)",
    )
    improvement_note: str | None = Field(
        None,
        description="Quick suggestion for improving this specific beat",
    )


# =============================================================================
# V2 MAIN SCHEMA
# =============================================================================


class EnhancedAdAnalysisV2(BaseModel):
    """
    Complete enhanced ad analysis V2 with all new capabilities.

    Extends the original EnhancedAdAnalysis while maintaining backward compatibility.
    The original fields remain at the top level.
    """

    # =========================================================================
    # METADATA
    # =========================================================================

    media_type: Literal["video", "image"] = Field(
        default="video",
        description="Whether this is a video or image ad",
    )
    analysis_version: str = Field(
        default="2.0",
        description="Schema version for forward compatibility",
    )
    analysis_confidence: float = Field(
        default=0.8,
        ge=0,
        le=1,
        description="Model's confidence in the analysis accuracy",
    )
    analysis_notes: list[str] = Field(
        default_factory=list,
        description="Any caveats or notes about the analysis",
    )

    # =========================================================================
    # EXISTING FIELDS (from EnhancedAdAnalysis V1) - PRESERVED FOR COMPATIBILITY
    # =========================================================================

    inferred_audience: str = Field(
        default="",
        description="Detailed target audience profile based on all visual and audio cues",
    )
    primary_messaging_pillar: str = Field(
        default="",
        description="Core message theme: e.g., 'Cost Savings', 'Premium Quality', 'Convenience'",
    )
    overall_pacing_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="1-10 score for pacing effectiveness",
    )
    production_style: ProductionStyleType = Field(
        default="Unknown",
        description="Overall production classification",
    )
    hook_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="1-10 score for first beat's attention-grabbing effectiveness",
    )
    timeline: list[EnhancedNarrativeBeat] = Field(
        default_factory=list,
        description="Ordered list of natural beats - VIDEO ONLY, empty for images",
    )
    overall_narrative_summary: str = Field(
        default="",
        description="2-3 sentence summary capturing the ad's story arc",
    )

    # =========================================================================
    # NEW TOP-LEVEL FIELDS
    # =========================================================================

    copy_analysis: CopyAnalysis = Field(
        default_factory=CopyAnalysis,
        description="Comprehensive text and copy analysis",
    )
    audio_analysis: AudioAnalysis | None = Field(
        None,
        description="Detailed audio layer analysis - VIDEO ONLY",
    )
    brand_elements: BrandElements = Field(
        default_factory=BrandElements,
        description="Brand presence and consistency analysis",
    )
    engagement_predictors: EngagementPredictors = Field(
        default_factory=EngagementPredictors,
        description="Signals that predict ad performance",
    )
    platform_optimization: PlatformOptimization = Field(
        default_factory=PlatformOptimization,
        description="Platform-specific signals and recommendations",
    )
    emotional_arc: EmotionalArc | None = Field(
        None,
        description="Emotional journey tracking - VIDEO ONLY",
    )
    critique: AdCritique = Field(
        default_factory=AdCritique,
        description="Comprehensive critique with actionable feedback",
    )
