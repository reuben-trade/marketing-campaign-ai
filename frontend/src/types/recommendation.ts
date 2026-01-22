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

export interface TestingVariant {
  variable: string;
  variant_a: string;
  variant_b: string;
  hypothesis: string;
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
  testing_variants?: TestingVariant[];
  success_metrics?: Record<string, unknown>;
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

export interface TrendAnalysis {
  visual_trends?: VisualTrend[];
  messaging_trends?: MessagingTrend[];
  cta_trends?: CTATrend[];
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
