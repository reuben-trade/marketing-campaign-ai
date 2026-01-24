export interface TargetAudience {
  demographics?: string;
  psychographics?: string;
  pain_points?: string[];
}

export interface BrandVoice {
  tone?: string;
  personality_traits?: string[];
  messaging_guidelines?: string;
}

export interface BusinessStrategy {
  id: string;
  business_name: string;
  business_description?: string;
  industry?: string;
  target_audience?: TargetAudience;
  brand_voice?: BrandVoice;
  market_position?: 'leader' | 'challenger' | 'niche';
  price_point?: 'premium' | 'mid-market' | 'budget';
  business_life_stage?: 'startup' | 'growth' | 'mature';
  unique_selling_points?: string[];
  competitive_advantages?: string[];
  marketing_objectives?: string[];
  raw_pdf_url?: string;
  extracted_date?: string;
  last_updated?: string;
}

export interface BusinessStrategyCreate {
  business_name: string;
  business_description?: string;
  industry?: string;
  target_audience?: TargetAudience;
  brand_voice?: BrandVoice;
  market_position?: 'leader' | 'challenger' | 'niche';
  price_point?: 'premium' | 'mid-market' | 'budget';
  business_life_stage?: 'startup' | 'growth' | 'mature';
  unique_selling_points?: string[];
  competitive_advantages?: string[];
  marketing_objectives?: string[];
}

export interface BusinessStrategyExtractResponse {
  strategy: BusinessStrategy;
  extraction_confidence: number;
  missing_fields: string[];
}
