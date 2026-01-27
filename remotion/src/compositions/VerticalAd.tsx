import React from 'react';
import { Composition } from 'remotion';
import { BaseAdComposition } from './BaseAdComposition';
import type { AdCompositionProps } from '../types';
import { COMPOSITION_DIMENSIONS, DEFAULT_FPS } from '../types';

/**
 * Vertical Ad Composition (9:16 aspect ratio)
 * For Stories, Reels, TikTok, YouTube Shorts
 * Resolution: 1080x1920
 */
export const VerticalAdComposition: React.FC<AdCompositionProps> = (props) => {
  return <BaseAdComposition {...props} />;
};

// Default props for the composition
const dims = COMPOSITION_DIMENSIONS.vertical_ad_v1;
const defaultProps: AdCompositionProps = {
  composition_id: 'vertical_ad_v1',
  width: dims.width,
  height: dims.height,
  fps: DEFAULT_FPS,
  duration_in_frames: 300,
  project_id: '00000000-0000-0000-0000-000000000000',
  timeline: [],
};

/**
 * Register the vertical ad composition with Remotion
 */
export const registerVerticalAd = () => {
  return (
    <Composition
      id="vertical_ad_v1"
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      component={VerticalAdComposition as any}
      durationInFrames={300}
      fps={DEFAULT_FPS}
      width={dims.width}
      height={dims.height}
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      defaultProps={defaultProps as any}
      calculateMetadata={({ props }) => {
        const p = props as unknown as AdCompositionProps;
        return {
          durationInFrames: p.duration_in_frames,
          fps: p.fps,
          width: p.width,
          height: p.height,
        };
      }}
    />
  );
};
