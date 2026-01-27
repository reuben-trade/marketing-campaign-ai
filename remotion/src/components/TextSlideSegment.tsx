import React from 'react';
import { Sequence, useCurrentFrame, spring, useVideoConfig, interpolate } from 'remotion';
import type { TextSlideContent, TextOverlay, Transition, BrandProfile } from '../types';
import { TextOverlayComponent } from './TextOverlay';
import { applyTransitionIn, applyTransitionOut } from '../utils/transitions';

interface Props {
  content: TextSlideContent;
  startFrame: number;
  durationFrames: number;
  brandProfile?: BrandProfile | null;
  overlay?: TextOverlay | null;
  transitionIn?: Transition | null;
  transitionOut?: Transition | null;
}

export const TextSlideSegment: React.FC<Props> = ({
  content,
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
  const backgroundColor = content.background_color || brandProfile?.primary_color || '#FF5733';
  const textColor = content.text_color || '#FFFFFF';
  const fontFamily = brandProfile?.font_family || 'Inter';

  // Animate headline entrance
  const headlineScale = spring({
    frame: localFrame,
    fps,
    config: {
      damping: 12,
      stiffness: 200,
      mass: 0.5,
    },
  });

  const headlineOpacity = interpolate(localFrame, [0, 10], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Animate subheadline with delay
  const subheadlineDelay = 10;
  const subheadlineScale = spring({
    frame: localFrame - subheadlineDelay,
    fps,
    config: {
      damping: 12,
      stiffness: 200,
      mass: 0.5,
    },
  });

  const subheadlineOpacity = interpolate(
    localFrame - subheadlineDelay,
    [0, 10],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }
  );

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
        }}
      >
        {/* Headline */}
        <h1
          style={{
            fontSize: 72,
            fontWeight: 'bold',
            color: textColor,
            fontFamily: `${fontFamily}, sans-serif`,
            textAlign: 'center',
            margin: 0,
            marginBottom: content.subheadline ? 24 : 0,
            transform: `scale(${headlineScale})`,
            opacity: headlineOpacity,
            lineHeight: 1.2,
          }}
        >
          {content.headline}
        </h1>

        {/* Subheadline */}
        {content.subheadline && (
          <h2
            style={{
              fontSize: 36,
              fontWeight: 'normal',
              color: textColor,
              fontFamily: `${fontFamily}, sans-serif`,
              textAlign: 'center',
              margin: 0,
              transform: `scale(${subheadlineScale})`,
              opacity: subheadlineOpacity,
              lineHeight: 1.4,
            }}
          >
            {content.subheadline}
          </h2>
        )}

        {/* Brand logo */}
        {brandProfile?.logo_url && (
          <img
            src={brandProfile.logo_url}
            alt="Brand logo"
            style={{
              position: 'absolute',
              bottom: 48,
              right: 48,
              maxHeight: 60,
              maxWidth: 120,
              objectFit: 'contain',
            }}
          />
        )}

        {/* Additional overlay */}
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
