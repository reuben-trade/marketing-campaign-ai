export interface ScriptBreakdown {
  hook?: {
    opening_line: string;
    timing: string;
    visual_cue?: string;
  };
  problem_agitation?: {
    pain_point: string;
    timing: string;
    emotional_trigger?: string;
  };
  solution_introduction?: {
    product_reveal: string;
    timing: string;
    key_benefit?: string;
  };
  social_proof?: {
    proof_type: string;
    timing: string;
    specifics?: string;
  };
  cta?: {
    action: string;
    timing: string;
    urgency_element?: string;
  };
}

export interface AdRecommendation {
  recommendation_id: number;
  priority: 'high' | 'medium' | 'low';
  ad_format: 'video' | 'image' | 'carousel';
  objective?: string;
  concept: {
    title: string;
    description: string;
    marketing_framework?: string;
  };
  visual_direction?: Record<string, unknown>;
  script_breakdown?: ScriptBreakdown;
  caption_strategy?: Record<string, unknown>;
  filming_requirements?: Record<string, unknown>;
  audio_design?: Record<string, unknown>;
  copywriting?: Record<string, unknown>;
  design_specifications?: Record<string, unknown>;
  targeting_alignment?: Record<string, unknown>;
  testing_variants?: string[];
  success_metrics?: Record<string, unknown>;
}

export interface TrendAnalysis {
  visual_trends?: string[];
  messaging_trends?: string[];
  cta_trends?: string[];
  engagement_patterns?: Record<string, unknown>;
}

export interface ImplementationRoadmap {
  phase_1_immediate?: string[];
  phase_2_support?: string[];
  testing_protocol?: Record<string, unknown>;
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
}

export interface RecommendationListResponse {
  items: Recommendation[];
  total: number;
  page: number;
  page_size: number;
}
