export interface BrandProfile {
  id: string;
  industry: string;
  niche: string | null;
  core_offer: string | null;
  competitors: string[] | null;
  keywords: string[] | null;
  tone: string | null;
  forbidden_terms: string[] | null;
  logo_url: string | null;
  primary_color: string | null;
  font_family: string | null;
  created_at: string;
  updated_at: string;
}

export interface BrandProfileCreate {
  industry: string;
  niche?: string;
  core_offer: string;
  competitors?: string[];
  keywords?: string[];
  tone?: string;
  forbidden_terms?: string[];
  logo_url?: string;
  primary_color?: string;
  font_family?: string;
}

export interface BrandProfileUpdate {
  industry?: string;
  niche?: string;
  core_offer?: string;
  competitors?: string[];
  keywords?: string[];
  tone?: string;
  forbidden_terms?: string[];
  logo_url?: string;
  primary_color?: string;
  font_family?: string;
}

export interface OnboardingStatusResponse {
  has_brand_profile: boolean;
  brand_profile: BrandProfile | null;
  completed_steps: number;
}

export interface IndustryOption {
  value: string;
  label: string;
}

export interface ToneOption {
  value: string;
  label: string;
}

// Onboarding form state for multi-step flow
export interface OnboardingFormData {
  // Step 1: Industry
  industry: string;
  niche: string;

  // Step 2: Core Offer
  core_offer: string;
  keywords: string[];
  tone: string;

  // Step 3: Competitors
  competitors: string[];
  forbidden_terms: string[];

  // Optional: Visual Identity
  logo_url: string;
  primary_color: string;
  font_family: string;
}

export const DEFAULT_ONBOARDING_FORM_DATA: OnboardingFormData = {
  industry: '',
  niche: '',
  core_offer: '',
  keywords: [],
  tone: '',
  competitors: [],
  forbidden_terms: [],
  logo_url: '',
  primary_color: '#3B82F6', // Default blue
  font_family: 'Inter',
};

// Predefined industry options (mirrors backend)
export const INDUSTRY_OPTIONS: IndustryOption[] = [
  { value: 'ecommerce', label: 'E-commerce / Retail' },
  { value: 'saas', label: 'SaaS / Software' },
  { value: 'home_services', label: 'Home Services' },
  { value: 'health_fitness', label: 'Health & Fitness' },
  { value: 'beauty_cosmetics', label: 'Beauty & Cosmetics' },
  { value: 'food_beverage', label: 'Food & Beverage' },
  { value: 'education', label: 'Education / Online Courses' },
  { value: 'finance', label: 'Finance / Fintech' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'automotive', label: 'Automotive' },
  { value: 'travel', label: 'Travel & Hospitality' },
  { value: 'entertainment', label: 'Entertainment / Media' },
  { value: 'legal', label: 'Legal Services' },
  { value: 'healthcare', label: 'Healthcare / Medical' },
  { value: 'technology', label: 'Technology / Electronics' },
  { value: 'other', label: 'Other' },
];

// Predefined tone options (mirrors backend)
export const TONE_OPTIONS: ToneOption[] = [
  { value: 'professional_friendly', label: 'Professional & Friendly' },
  { value: 'casual', label: 'Casual & Conversational' },
  { value: 'authoritative', label: 'Authoritative & Expert' },
  { value: 'playful', label: 'Playful & Fun' },
  { value: 'luxurious', label: 'Luxurious & Premium' },
  { value: 'urgent', label: 'Urgent & Action-Oriented' },
  { value: 'empathetic', label: 'Empathetic & Understanding' },
  { value: 'inspirational', label: 'Inspirational & Motivational' },
];
