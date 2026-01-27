import React from 'react';
import { Composition } from 'remotion';
import { BaseAdComposition } from './BaseAdComposition';
import type { AdCompositionProps } from '../types';
import { COMPOSITION_DIMENSIONS, DEFAULT_FPS } from '../types';

/**
 * Horizontal Ad Composition (16:9 aspect ratio)
 * For YouTube, Facebook Feed, LinkedIn
 * Resolution: 1920x1080
 */
export const HorizontalAdComposition: React.FC<AdCompositionProps> = (props) => {
  return <BaseAdComposition {...props} />;
};

// Default props for the composition
const dims = COMPOSITION_DIMENSIONS.horizontal_ad_v1;
const defaultProps: AdCompositionProps = {
  composition_id: 'horizontal_ad_v1',
  width: dims.width,
  height: dims.height,
  fps: DEFAULT_FPS,
  duration_in_frames: 300,
  project_id: '00000000-0000-0000-0000-000000000000',
  timeline: [],
};

/**
 * Register the horizontal ad composition with Remotion
 */
export const registerHorizontalAd = () => {
  return (
    <Composition
      id="horizontal_ad_v1"
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      component={HorizontalAdComposition as any}
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
