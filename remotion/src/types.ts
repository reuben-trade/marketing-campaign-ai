/**
 * TypeScript types matching the backend RemotionPayload schema.
 * Keep in sync with app/schemas/remotion_payload.py
 */

export type CompositionType = 'vertical_ad_v1' | 'horizontal_ad_v1' | 'square_ad_v1';

export type SegmentType =
  | 'video_clip'
  | 'generated_broll'
  | 'text_slide'
  | 'b_roll_overlay'
  | 'title_card'
  | 'caption_overlay';

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

export interface BrandProfile {
  primary_color?: string;
  font_family?: string;
  logo_url?: string | null;
}

export interface AudioTrack {
  url: string;
  volume?: number;
  fade_in_frames?: number;
  fade_out_frames?: number;
}

export interface TextOverlay {
  text: string;
  position?: TextPosition;
  font_size?: number;
  font_weight?: string;
  color?: string;
  background?: string | null;
  animation?: TextAnimation;
}

export interface Transition {
  type: TransitionType;
  duration_frames?: number;
}

export interface VideoClipSource {
  url: string;
  start_time: number;
  end_time: number;
}

export interface GeneratedBRollSource {
  url?: string | null;
  generation_prompt: string;
  regenerate_available?: boolean;
}

export interface TextSlideContent {
  headline: string;
  subheadline?: string | null;
  background_color?: string;
  text_color?: string;
}

/**
 * Animation style for title card text elements.
 */
export type TitleAnimation =
  | 'fade_up'
  | 'fade_down'
  | 'scale_in'
  | 'slide_left'
  | 'slide_right'
  | 'typewriter'
  | 'none';

/**
 * Layout style for the title card.
 */
export type TitleCardLayout = 'centered' | 'left_aligned' | 'right_aligned' | 'stacked';

/**
 * Style variants for caption overlays.
 */
export type CaptionStyle = 'minimal' | 'bar' | 'karaoke';

/**
 * Position options for captions.
 */
export type CaptionPosition = 'top' | 'center' | 'bottom';

/**
 * A single word with timestamp information for word-level sync.
 */
export interface TranscriptWord {
  word: string;
  start: number; // Start time in seconds
  end: number; // End time in seconds
}

/**
 * A single caption entry with timing and optional highlighting.
 */
export interface CaptionEntry {
  text: string;
  start_time: number; // Start time in seconds
  end_time: number; // End time in seconds
  highlight_words?: string[] | null; // Power words to highlight
}

/**
 * Configuration for caption overlay display.
 * Supports word-level sync, power word highlighting, and multiple styles.
 */
export interface CaptionOverlayConfig {
  // Caption content - either captions array or transcript_words for word-level sync
  captions?: CaptionEntry[] | null;
  transcript_words?: TranscriptWord[] | null;

  // Display settings
  style?: CaptionStyle;
  position?: CaptionPosition;
  max_words_per_line?: number; // For word-level display (default 5)

  // Text styling
  font_size?: number;
  font_family?: string;
  text_color?: string;
  highlight_color?: string; // Color for power words
  background_color?: string; // Background for bar style
  background_opacity?: number;

  // Animation
  word_animation?: 'none' | 'pop' | 'fade';

  // Additional power words to highlight (in addition to per-caption highlights)
  power_words?: string[] | null;
}

/**
 * Content for a title card segment.
 * Title cards are animated text screens with branding support.
 */
export interface TitleCardContent {
  headline: string;
  subheadline?: string | null;
  tagline?: string | null;
  background_color?: string;
  text_color?: string;
  accent_color?: string;
  animation?: TitleAnimation;
  layout?: TitleCardLayout;
  show_logo?: boolean;
  logo_position?: 'top' | 'bottom' | 'behind';
  background_gradient?: {
    start_color: string;
    end_color: string;
    angle?: number;
  } | null;
  background_image_url?: string | null;
  background_image_opacity?: number;
}

/**
 * B-Roll overlay source for J-Cut/L-Cut video editing.
 * Overlays video on top while maintaining the main audio track.
 */
export interface BRollOverlaySource {
  // Main video that provides the continuous audio track
  main_video: VideoClipSource;
  // B-Roll video that overlays on top (video only, no audio)
  overlay_video: VideoClipSource;
  // When to start the overlay relative to segment start (in frames)
  overlay_start_offset_frames?: number;
  // Duration of the overlay in frames (if different from segment duration)
  overlay_duration_frames?: number;
  // Opacity of the overlay video (0-1)
  overlay_opacity?: number;
  // Position/scale of the overlay (for picture-in-picture effects)
  overlay_position?: 'full' | 'top-right' | 'bottom-right' | 'top-left' | 'bottom-left';
  overlay_scale?: number;
  // Transition for the overlay appearing/disappearing
  overlay_transition_in?: Transition | null;
  overlay_transition_out?: Transition | null;
}

export interface TimelineSegment {
  id: string;
  type: SegmentType;
  start_frame: number;
  duration_frames: number;

  // Source - one of these will be populated based on type
  source?: VideoClipSource | null;
  generated_source?: GeneratedBRollSource | null;
  text_content?: TextSlideContent | null;
  broll_overlay_source?: BRollOverlaySource | null;
  title_card_content?: TitleCardContent | null;

  // Visual overlays
  overlay?: TextOverlay | null;

  // Caption overlay configuration for word-level synced captions
  caption_overlay?: CaptionOverlayConfig | null;

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

// Composition-specific props (extends RemotionPayload for type safety)
export interface AdCompositionProps extends RemotionPayload {
  // Additional props can be added here
}

// Dimension presets for each composition type
export const COMPOSITION_DIMENSIONS: Record<
  CompositionType,
  { width: number; height: number }
> = {
  vertical_ad_v1: { width: 1080, height: 1920 },
  horizontal_ad_v1: { width: 1920, height: 1080 },
  square_ad_v1: { width: 1080, height: 1080 },
};

// Default values
export const DEFAULT_FPS = 30;
export const DEFAULT_BRAND_PROFILE: BrandProfile = {
  primary_color: '#FF5733',
  font_family: 'Inter',
  logo_url: null,
};
