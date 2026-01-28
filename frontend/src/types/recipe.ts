// Recipe types matching backend schemas

export interface BeatDefinition {
  beat_type: string;
  target_duration: number;
  characteristics: string[];
  purpose: string;
  cinematics: Record<string, unknown> | null;
  rhetorical_mode: string | null;
  text_overlay_pattern: string | null;
  transition_out: string | null;
}

export interface Recipe {
  id: string;
  source_ad_id: string | null;
  name: string;
  total_duration_seconds: number | null;
  structure: BeatDefinition[];
  pacing: string | null;
  style: string | null;
  composite_score: number | null;
  created_at: string;
}

export interface RecipeListResponse {
  recipes: Recipe[];
  total: number;
}

export interface RecipeFilters {
  limit?: number;
  offset?: number;
  style?: string;
  pacing?: string;
  min_score?: number;
}

export interface RecipeExtractRequest {
  ad_id: string;
  name?: string;
}

export interface RecipeExtractResponse {
  recipe: Recipe;
  extraction_notes: string[];
}

export interface ReferenceAdFetchRequest {
  url: string;
  name?: string;
}

export interface ReferenceAdResponse {
  ad_id: string;
  recipe: Recipe | null;
  status: 'success' | 'partial' | 'error';
  message: string;
  processing_notes: string[];
}
