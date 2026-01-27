import React from 'react';
import { Audio, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import type { AudioTrack as AudioTrackProps } from '../types';

interface Props extends AudioTrackProps {
  totalDurationFrames: number;
}

/**
 * Audio track component with fade in/out support.
 */
export const AudioTrackComponent: React.FC<Props> = ({
  url,
  volume = 0.8,
  fade_in_frames = 15,
  fade_out_frames = 30,
  totalDurationFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Calculate volume with fade in/out
  let currentVolume = volume;

  // Fade in
  if (fade_in_frames > 0 && frame < fade_in_frames) {
    currentVolume = interpolate(frame, [0, fade_in_frames], [0, volume], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
  }

  // Fade out
  const fadeOutStart = totalDurationFrames - fade_out_frames;
  if (fade_out_frames > 0 && frame > fadeOutStart) {
    currentVolume = interpolate(
      frame,
      [fadeOutStart, totalDurationFrames],
      [volume, 0],
      {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      }
    );
  }

  return (
    <Audio
      src={url}
      volume={currentVolume}
      loop
    />
  );
};
