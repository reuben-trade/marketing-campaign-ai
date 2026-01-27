import React from 'react';
import { OffthreadVideo, Sequence, useCurrentFrame, useVideoConfig, Img } from 'remotion';
import type { GeneratedBRollSource, TextOverlay, Transition, BrandProfile } from '../types';
import { TextOverlayComponent } from './TextOverlay';
import { applyTransitionIn, applyTransitionOut } from '../utils/transitions';

interface Props {
  source: GeneratedBRollSource;
  startFrame: number;
  durationFrames: number;
  brandProfile?: BrandProfile | null;
  overlay?: TextOverlay | null;
  transitionIn?: Transition | null;
  transitionOut?: Transition | null;
}

/**
 * B-Roll segment component that displays AI-generated video content.
 * Shows a placeholder if the video hasn't been generated yet.
 */
export const BRollSegment: React.FC<Props> = ({
  source,
  startFrame,
  durationFrames,
  brandProfile,
  overlay,
  transitionIn,
  transitionOut,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const localFrame = frame - startFrame;
  const backgroundColor = brandProfile?.primary_color || '#1a1a2e';

  // Get transition styles
  const transInStyle = applyTransitionIn(
    transitionIn?.type || 'cut',
    localFrame,
    transitionIn?.duration_frames || 0,
    width,
    height
  );
  const transOutStyle = applyTransitionOut(
    transitionOut?.type || 'cut',
    localFrame,
    durationFrames,
    transitionOut?.duration_frames || 0,
    width,
    height
  );

  const combinedOpacity = (transInStyle.opacity ?? 1) * (transOutStyle.opacity ?? 1);
  const combinedScale = (transInStyle.scale ?? 1) * (transOutStyle.scale ?? 1);

  // If we have a generated video URL, show it
  if (source.url) {
    return (
      <Sequence from={startFrame} durationInFrames={durationFrames}>
        <div
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            opacity: combinedOpacity,
            transform: `scale(${combinedScale})`,
          }}
        >
          <OffthreadVideo
            src={source.url}
            style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
          {overlay && (
            <TextOverlayComponent
              {...overlay}
              segmentStartFrame={startFrame}
            />
          )}
        </div>
      </Sequence>
    );
  }

  // Placeholder for when B-Roll hasn't been generated yet
  return (
    <Sequence from={startFrame} durationInFrames={durationFrames}>
      <div
        style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          backgroundColor,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: 48,
          opacity: combinedOpacity,
          transform: `scale(${combinedScale})`,
        }}
      >
        {/* Placeholder icon */}
        <div
          style={{
            width: 120,
            height: 120,
            borderRadius: 60,
            backgroundColor: 'rgba(255,255,255,0.1)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            marginBottom: 24,
          }}
        >
          <svg
            width="60"
            height="60"
            viewBox="0 0 24 24"
            fill="none"
            stroke="rgba(255,255,255,0.5)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
            <line x1="7" y1="2" x2="7" y2="22" />
            <line x1="17" y1="2" x2="17" y2="22" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <line x1="2" y1="7" x2="7" y2="7" />
            <line x1="2" y1="17" x2="7" y2="17" />
            <line x1="17" y1="17" x2="22" y2="17" />
            <line x1="17" y1="7" x2="22" y2="7" />
          </svg>
        </div>

        {/* Generating label */}
        <span
          style={{
            fontSize: 24,
            color: 'rgba(255,255,255,0.7)',
            fontFamily: 'Inter, sans-serif',
            marginBottom: 12,
          }}
        >
          AI B-Roll
        </span>

        {/* Prompt preview */}
        <span
          style={{
            fontSize: 16,
            color: 'rgba(255,255,255,0.4)',
            fontFamily: 'Inter, sans-serif',
            textAlign: 'center',
            maxWidth: '80%',
            lineHeight: 1.4,
          }}
        >
          "{source.generation_prompt}"
        </span>

        {overlay && (
          <TextOverlayComponent
            {...overlay}
            segmentStartFrame={startFrame}
          />
        )}
      </div>
    </Sequence>
  );
};
