/**
 * Main entry point for the Remotion video compositions.
 * 
 * This package provides three ad compositions:
 * - vertical_ad_v1 (9:16) - Stories, Reels, TikTok, YouTube Shorts
 * - horizontal_ad_v1 (16:9) - YouTube, Facebook Feed, LinkedIn
 * - square_ad_v1 (1:1) - Instagram Feed, Facebook Feed
 * 
 * Usage:
 * - For Remotion Studio: import { RemotionRoot } from './Root'
 * - For Player: import compositions directly from './compositions'
 * - For programmatic rendering: use the render service API
 */

// Re-export types
export * from './types';

// Re-export compositions
export {
  BaseAdComposition,
  VerticalAdComposition,
  HorizontalAdComposition,
  SquareAdComposition,
} from './compositions';

// Re-export components for custom compositions
export {
  TextOverlayComponent,
  VideoClipSegment,
  TextSlideSegment,
  BRollSegment,
  AudioTrackComponent,
} from './components';

// Re-export Root for Remotion CLI
export { RemotionRoot } from './Root';
