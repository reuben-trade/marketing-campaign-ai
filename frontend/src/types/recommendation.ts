export interface ColorPalette {
  primary: string;
  secondary: string;
  accent: string;
  reasoning?: string;
  background?: string;
  text?: string;
}

export interface VisualDirection {
  overall_style?: string;
  setting?: string;
  color_palette?: ColorPalette;
  composition?: string;
  camera_work?: string;
  layout?: string;
  style?: string;
}

export interface ScriptSection {
  timing?: string;
  visual_description?: string;
  action?: string;
  audio?: string;
  voiceover?: string;
  on_screen_text?: string;
  text_style?: string;
  why_this_works?: string;
  product_demo?: string;
  text_overlay?: string;
  urgency_element?: string;
  opening_line?: string;
  pain_point?: string;
  product_reveal?: string;
}

export interface ScriptBreakdown {
  hook?: ScriptSection;
  problem_agitation?: ScriptSection;
  solution_introduction?: ScriptSection;
  social_proof?: ScriptSection;
  cta?: ScriptSection;
}

export interface CaptionStrategy {
  necessity: string;
  font: string;
  size: string;
  placement: string;
  timing: string;
  animations: string;
  emoji_usage: string;
  background: string;
}

export interface ShotRequirement {
  shot_type: string;
  description: string;
  duration: string;
  purpose: string;
}

export interface FilmingRequirements {
  shots_needed: ShotRequirement[];
  b_roll: string[];
  talent?: string;
  props?: string;
}

export interface MusicSpec {
  style: string;
  tempo: string;
  energy: string;
  when: string;
  reference?: string;
}

export interface VoiceoverSpec {
  tone: string;
  gender: string;
  pace: string;
  emphasis: string;
}

export interface AudioDesign {
  music?: MusicSpec;
  sound_effects: string[];
  voiceover?: VoiceoverSpec;
}

export interface CopyElement {
  text: string;
  placement: string;
  font?: string;
  color?: string;
  size?: string;
  style?: string;
}

export interface Copywriting {
  headline?: CopyElement;
  subheadline?: CopyElement;
  body_copy?: CopyElement;
  cta_button?: CopyElement;
}

export interface ContentSection {
  visual: string;
  text: string;
  style: string;
}

export interface ContentBreakdown {
  left_side_problem?: ContentSection;
  right_side_solution?: ContentSection;
  center_divider?: string;
}

export interface DesignSpecifications {
  dimensions?: string;
  file_format?: string;
  file_size?: string;
  safe_zones?: string;
  text_coverage?: string;
  contrast_ratio?: string;
  mobile_optimization?: string;
  font?: string;
  colors?: Record<string, string>;
}

export interface ProductionNotes {
  tools?: string;
  assets_needed?: string[];
  time_estimate?: string;
  talent?: string;
  notes?: string;
}

export interface TestingVariant {
  variable: string;
  variant_a: string;
  variant_b: string;
  hypothesis: string;
}

export interface TargetingAlignment {
  audience: string;
  pain_point_addressed: string;
  brand_voice_alignment: string;
  price_point_justification: string;
}

export interface SuccessMetrics {
  primary?: string;
  secondary: string[];
  optimization?: string;
}

export interface AdRecommendation {
  recommendation_id: number;
  priority: 'high' | 'medium' | 'low';
  ad_format: 'video' | 'image' | 'carousel';
  objective?: string;
  duration?: string;
  concept?: {
    title: string;
    description: string;
    marketing_framework?: string;
  } | null;
  visual_direction?: VisualDirection;
  // Video-specific fields
  script_breakdown?: ScriptBreakdown;
  caption_strategy?: CaptionStrategy;
  filming_requirements?: FilmingRequirements;
  audio_design?: AudioDesign;
  // Image-specific fields
  content_breakdown?: ContentBreakdown;
  copywriting?: Copywriting;
  design_specifications?: DesignSpecifications;
  production_notes?: ProductionNotes;
  // Common fields
  targeting_alignment?: TargetingAlignment;
  testing_variants?: TestingVariant[];
  success_metrics?: SuccessMetrics;
}

export interface VisualTrend {
  trend: string;
  prevalence: string;
  description: string;
  why_it_works: string;
  example_ad_ids: string[];
}

export interface MessagingTrend {
  trend: string;
  prevalence: string;
  description: string;
  why_it_works: string;
  example_ad_ids: string[];
}

export interface CTATrend {
  trend: string;
  examples: string[];
  effectiveness: string;
}

export interface EngagementPatterns {
  best_performing_length?: string;
  optimal_posting_time?: string;
  hook_timing?: string;
}

export interface TrendAnalysis {
  visual_trends?: VisualTrend[];
  messaging_trends?: MessagingTrend[];
  cta_trends?: CTATrend[];
  engagement_patterns?: EngagementPatterns;
}

export interface ImplementationPhase {
  action: string;
  rationale: string;
  timeline: string;
  budget_allocation: string;
}

export interface TestingProtocol {
  duration: string;
  kpis: string[];
  decision_criteria: string;
}

export interface ImplementationRoadmap {
  phase_1_immediate?: ImplementationPhase;
  phase_2_support?: ImplementationPhase;
  testing_protocol?: TestingProtocol;
}

export interface Recommendation {
  id: string;
  generated_date: string;
  top_n_ads: number;
  date_range_start?: string;
  date_range_end?: string;
  executive_summary?: string;
  trend_analysis?: TrendAnalysis;
  recommendations: AdRecommendation[];
  implementation_roadmap?: ImplementationRoadmap;
  ads_analyzed: string[];
  generation_time_seconds: number;
  model_used: string;
}

export interface RecommendationGenerateRequest {
  top_n_ads?: number;
  date_range_start?: string;
  date_range_end?: string;
  focus_areas?: string[];
  num_video_ideas?: number;
  num_image_ideas?: number;
  user_ad_id?: string;
  relevance_description?: string;
  relevance_themes?: string[];
  min_similarity?: number;
}

export interface RecommendationListResponse {
  items: Recommendation[];
  total: number;
  page: number;
  page_size: number;
}
