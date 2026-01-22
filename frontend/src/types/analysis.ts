export type BeatType =
  | 'Hook'
  | 'Problem'
  | 'Solution'
  | 'Product Showcase'
  | 'Social Proof'
  | 'Benefit Stack'
  | 'Objection Handling'
  | 'CTA'
  | 'Transition'
  | 'Unknown';

export type RhetoricalMode = 'Logos' | 'Pathos' | 'Ethos' | 'Kairos' | 'Unknown';

export interface TextOverlay {
  text: string;
  timestamp: string;
  duration_seconds: number;
  position: string;
  typography?: string;
  animation?: string;
  emphasis_type?: string;
  purpose?: string;
}

export interface Cinematics {
  camera_angle: string;
  lighting_style: string;
  cinematic_features: string[];
  color_grading?: string;
  motion_type?: string;
  transition_in?: string;
  transition_out?: string;
}

export interface RhetoricalAppeal {
  mode: RhetoricalMode;
  description: string;
  secondary_mode?: RhetoricalMode;
  persuasion_techniques: string[];
  objection_addressed?: string;
}

export interface EnhancedNarrativeBeat {
  start_time: string; // MM:SS format
  end_time: string; // MM:SS format
  beat_type: BeatType;
  visual_description: string;
  audio_transcript: string;
  emotion?: string;
  emotion_intensity?: number;
  tone_of_voice: string;
  target_audience_cues: string;
  attention_score?: number;
  improvement_note?: string;
  cinematics: Cinematics;
  rhetorical_appeal: RhetoricalAppeal;
  text_overlays_in_beat: TextOverlay[];
  key_visual_elements: string[];
}

export interface StrengthItem {
  strength: string;
  evidence: string;
  timestamp?: string;
  impact: string;
}

export interface WeaknessItem {
  weakness: string;
  evidence: string;
  timestamp?: string;
  impact: string;
  suggested_fix: string;
}

export interface RemakeSuggestion {
  section_to_remake: string;
  current_approach: string;
  suggested_approach: string;
  expected_improvement: string;
  effort_level: 'minor tweak' | 'moderate edit' | 'full reshoot';
  priority: 'high' | 'medium' | 'low';
}

export interface AdCritique {
  overall_grade: string;
  overall_assessment: string;
  strengths: StrengthItem[];
  weaknesses: WeaknessItem[];
  remake_suggestions: RemakeSuggestion[];
  quick_wins: string[];
  competitive_position?: string;
}

export interface CopyAnalysis {
  copy_framework?: string;
  headline_text?: string;
  cta_text?: string;
  power_words: string[];
  sensory_words: string[];
  text_overlays: TextOverlay[];
}

export interface AudioAnalysis {
  music_genre?: string;
  music_tempo?: string;
  music_energy_level?: string;
  music_mood?: string;
  music_sync_moments: string[];
  drop_timestamps: string[];
  has_voiceover: boolean;
  voice_gender?: string;
  voice_age_range?: string;
  voice_tone?: string;
  estimated_wpm?: number;
  sound_effects: Array<{
    timestamp: string;
    sfx_type: string;
    purpose?: string;
  }>;
  silence_moments: string[];
  audio_visual_sync_score?: number;
}

export interface BrandElements {
  logo_appearances: Array<{
    timestamp: string;
    duration_seconds: number;
    position: string;
    size: string;
    animation?: string;
  }>;
  product_appearances: Array<{
    timestamp: string;
    duration_seconds: number;
    shot_type: string;
    prominence: string;
    context?: string;
  }>;
  brand_colors: string[];
  product_visibility_seconds?: number;
}

export interface EngagementPredictors {
  first_frame_hook?: string;
  pattern_interrupt_type?: string;
  curiosity_gap: boolean;
  visual_contrast_score?: number;
  thumb_stop_score: number;
  scene_change_frequency?: string;
  visual_variety_score?: number;
  uses_social_proof: boolean;
  uses_fomo: boolean;
  uses_transformation: boolean;
  predicted_watch_through_rate?: string;
  predicted_engagement_type?: string;
}

export interface PlatformOptimization {
  aspect_ratio?: string;
  optimal_platforms: string[];
  sound_off_compatible: boolean;
  caption_dependency?: string;
  duration_assessment?: string;
  safe_zone_compliance: boolean;
}

export interface EmotionalArc {
  emotional_beats: Array<{
    timestamp: string;
    primary_emotion: string;
    intensity: number;
    trigger?: string;
  }>;
  emotional_climax_timestamp?: string;
  tension_build_pattern?: string;
  resolution_type?: string;
  dominant_emotional_tone?: string;
}

export interface EnhancedAdAnalysisV2 {
  media_type: 'video' | 'image';
  analysis_version: string;
  analysis_confidence: number;
  analysis_notes: string[];

  // Core fields
  inferred_audience: string;
  primary_messaging_pillar: string;
  overall_pacing_score: number;
  production_style: string;
  hook_score: number;
  timeline: EnhancedNarrativeBeat[];
  overall_narrative_summary: string;

  // Extended analysis
  copy_analysis?: CopyAnalysis;
  audio_analysis?: AudioAnalysis;
  brand_elements?: BrandElements;
  engagement_predictors?: EngagementPredictors;
  platform_optimization?: PlatformOptimization;
  emotional_arc?: EmotionalArc;
  critique: AdCritique;

  // Additional scores
  thumb_stop_score?: number;
  native_feel_score?: number;
}
