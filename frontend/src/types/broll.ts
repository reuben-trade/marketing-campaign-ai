/**
 * Types for B-Roll generation API.
 * Matches backend schemas at app/schemas/veo_request.py
 */

// Enums
export type VeoAspectRatio = '9:16' | '16:9' | '1:1';
export type VeoStyle = 'realistic' | 'cinematic' | 'animated' | 'artistic';
export type VeoGenerationStatus = 'pending' | 'processing' | 'completed' | 'failed';

// Generated clip variant
export interface VeoGeneratedClip {
  id: string;
  url: string | null;
  thumbnail_url: string | null;
  duration_seconds: number;
  width: number;
  height: number;
  file_size_bytes: number | null;
  variant_index: number;
}

// Generate request
export interface VeoGenerateRequest {
  prompt: string;
  duration_seconds?: number;
  aspect_ratio?: VeoAspectRatio;
  style?: VeoStyle;
  num_variants?: number;
  project_id?: string | null;
  slot_id?: string | null;
  negative_prompt?: string | null;
  seed?: number | null;
}

// Regenerate request
export interface VeoRegenerateRequest {
  original_generation_id: string;
  prompt?: string | null;
  duration_seconds?: number | null;
  style?: VeoStyle | null;
  num_variants?: number | null;
  negative_prompt?: string | null;
}

// Generation response
export interface VeoGenerationResponse {
  id: string;
  status: VeoGenerationStatus;
  prompt: string;
  duration_seconds: number;
  aspect_ratio: VeoAspectRatio;
  style: VeoStyle;
  num_variants: number;
  clips: VeoGeneratedClip[];
  error_message: string | null;
  project_id: string | null;
  slot_id: string | null;
  created_at: string;
  completed_at: string | null;
  generation_time_seconds: number | null;
}

// Generation status response (for polling)
export interface VeoGenerationStatusResponse {
  id: string;
  status: VeoGenerationStatus;
  progress: number;
  clips: VeoGeneratedClip[];
  error_message: string | null;
  estimated_time_remaining_seconds: number | null;
}

// Generation list response
export interface VeoGenerationListResponse {
  generations: VeoGenerationResponse[];
  total: number;
  page: number;
  page_size: number;
}

// Select clip request
export interface VeoSelectClipRequest {
  generation_id: string;
  clip_id: string;
}

// Select clip response
export interface VeoSelectClipResponse {
  clip: VeoGeneratedClip;
  storage_url: string;
}

// Prompt enhancement request
export interface PromptEnhancementRequest {
  original_prompt: string;
  context?: string | null;
  style_hints?: string[] | null;
}

// Prompt enhancement response
export interface PromptEnhancementResponse {
  original_prompt: string;
  enhanced_prompts: string[];
  style_recommendations: VeoStyle[];
}

// Aspect ratio display names
export const ASPECT_RATIO_LABELS: Record<VeoAspectRatio, string> = {
  '9:16': 'Vertical (9:16)',
  '16:9': 'Horizontal (16:9)',
  '1:1': 'Square (1:1)',
};

// Style display names
export const STYLE_LABELS: Record<VeoStyle, string> = {
  realistic: 'Realistic',
  cinematic: 'Cinematic',
  animated: 'Animated',
  artistic: 'Artistic',
};

// Status display info
export const STATUS_INFO: Record<VeoGenerationStatus, { label: string; color: string }> = {
  pending: { label: 'Pending', color: 'yellow' },
  processing: { label: 'Generating...', color: 'blue' },
  completed: { label: 'Completed', color: 'green' },
  failed: { label: 'Failed', color: 'red' },
};
