/**
 * Types for video rendering API.
 * Matches backend schemas at app/schemas/render.py and app/schemas/remotion_payload.py
 */

// Enums
export type CompositionType = 'vertical_ad_v1' | 'horizontal_ad_v1' | 'square_ad_v1';
export type SegmentType = 'video_clip' | 'generated_broll' | 'text_slide';
export type TransitionType =
  | 'cut'
  | 'dissolve'
  | 'fade'
  | 'wipe_right'
  | 'wipe_left'
  | 'slide_up'
  | 'slide_down'
  | 'zoom_in'
  | 'zoom_out';
export type TextAnimation = 'none' | 'fade_in' | 'pop_in' | 'slide_up' | 'typewriter';
export type TextPosition = 'top' | 'center' | 'bottom' | 'lower-third';
export type RenderStatus = 'pending' | 'rendering' | 'completed' | 'failed';
export type RenderMode = 'local' | 'lambda';

// Brand profile styling
export interface BrandProfile {
  primary_color?: string;
  font_family?: string;
  logo_url?: string | null;
}

// Audio track configuration
export interface AudioTrack {
  url: string;
  volume?: number;
  fade_in_frames?: number;
  fade_out_frames?: number;
}

// Text overlay on a segment
export interface TextOverlay {
  text: string;
  position?: TextPosition;
  font_size?: number;
  font_weight?: string;
  color?: string;
  background?: string | null;
  animation?: TextAnimation;
}

// Transition configuration
export interface Transition {
  type: TransitionType;
  duration_frames?: number;
}

// Source for video clip segment
export interface VideoClipSource {
  url: string;
  start_time: number;
  end_time: number;
}

// Source for AI-generated B-Roll
export interface GeneratedBRollSource {
  url?: string | null;
  generation_prompt: string;
  regenerate_available?: boolean;
}

// Content for text slide segment
export interface TextSlideContent {
  headline: string;
  subheadline?: string | null;
  background_color?: string;
  text_color?: string;
}

// Timeline segment in the video
export interface TimelineSegment {
  id: string;
  type: SegmentType;
  start_frame: number;
  duration_frames: number;

  // Source - one of these based on type
  source?: VideoClipSource | null;
  generated_source?: GeneratedBRollSource | null;
  text_content?: TextSlideContent | null;

  // Visual overlays
  overlay?: TextOverlay | null;

  // Transitions
  transition_in?: Transition | null;
  transition_out?: Transition | null;

  // Metadata from visual script
  beat_type?: string | null;
  slot_id?: string | null;

  // Search metadata (for clip replacement UI)
  search_query?: string | null;
  similarity_score?: number | null;
  alternative_clips?: Record<string, unknown>[] | null;
}

// Complete Remotion payload
export interface RemotionPayload {
  composition_id: CompositionType;
  width: number;
  height: number;
  fps: number;
  duration_in_frames: number;

  // Props passed to Remotion composition
  project_id: string;
  visual_script_id?: string | null;
  brand_profile?: BrandProfile | null;
  audio_track?: AudioTrack | null;
  timeline: TimelineSegment[];

  // Metadata
  created_at?: string | null;
  version?: number;

  // Gap/issue tracking
  gaps?: Record<string, unknown>[] | null;
  warnings?: string[] | null;
}

// Render request
export interface RenderRequest {
  project_id: string;
  payload: RemotionPayload;
  mode?: RenderMode;
  priority?: number;
}

// Render response
export interface RenderResponse {
  id: string;
  project_id: string;
  composition_id: string;
  status: RenderStatus;
  created_at: string;
  video_url?: string | null;
  thumbnail_url?: string | null;
  duration_seconds?: number | null;
  file_size_bytes?: number | null;
  render_time_seconds?: number | null;
  error_message?: string | null;
}

// Detailed render status response
export interface RenderStatusResponse extends RenderResponse {
  progress: number;
  started_at?: string | null;
  completed_at?: string | null;
}

// Render list response
export interface RenderListResponse {
  renders: RenderResponse[];
  total: number;
  page: number;
  page_size: number;
}

// Render queue stats
export interface RenderQueueStats {
  pending_count: number;
  rendering_count: number;
  completed_today: number;
  failed_today: number;
  avg_render_time_seconds?: number | null;
}

// Composition dimensions
export const COMPOSITION_DIMENSIONS: Record<CompositionType, { width: number; height: number }> = {
  vertical_ad_v1: { width: 1080, height: 1920 },
  horizontal_ad_v1: { width: 1920, height: 1080 },
  square_ad_v1: { width: 1080, height: 1080 },
};

export const DEFAULT_FPS = 30;
