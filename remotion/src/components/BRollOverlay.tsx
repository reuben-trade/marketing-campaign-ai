import React from 'react';
import {
  OffthreadVideo,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type { BRollOverlaySource, TextOverlay, Transition, BrandProfile } from '../types';
import { TextOverlayComponent } from './TextOverlay';
import { applyTransitionIn, applyTransitionOut } from '../utils/transitions';

interface Props {
  source: BRollOverlaySource;
  startFrame: number;
  durationFrames: number;
  brandProfile?: BrandProfile | null;
  overlay?: TextOverlay | null;
  transitionIn?: Transition | null;
  transitionOut?: Transition | null;
}

/**
 * B-Roll Overlay component for J-Cut/L-Cut video editing.
 *
 * This component renders a main video with continuous audio while overlaying
 * a B-Roll video on top. This enables professional editing techniques:
 *
 * - J-Cut: Audio from the next clip starts before the visual cuts
 * - L-Cut: Audio from the current clip continues over the next visual
 *
 * The main video provides continuous audio, while the overlay video
 * appears/disappears with optional transitions, creating visual interest
 * while maintaining audio continuity.
 */
export const BRollOverlay: React.FC<Props> = ({
  source,
  startFrame,
  durationFrames,
  overlay,
  transitionIn,
  transitionOut,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const localFrame = frame - startFrame;

  const {
    main_video,
    overlay_video,
    overlay_start_offset_frames = 0,
    overlay_duration_frames,
    overlay_opacity = 1,
    overlay_position = 'full',
    overlay_scale = 1,
    overlay_transition_in,
    overlay_transition_out,
  } = source;

  // Calculate overlay timing
  const overlayDuration = overlay_duration_frames ?? durationFrames - overlay_start_offset_frames;
  const overlayEndFrame = overlay_start_offset_frames + overlayDuration;

  // Main segment transition styles
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

  const mainOpacity = (transInStyle.opacity ?? 1) * (transOutStyle.opacity ?? 1);
  const mainScale = (transInStyle.scale ?? 1) * (transOutStyle.scale ?? 1);
  const mainTranslateX = (transInStyle.translateX ?? 0) + (transOutStyle.translateX ?? 0);
  const mainTranslateY = (transInStyle.translateY ?? 0) + (transOutStyle.translateY ?? 0);

  // Calculate overlay transition styles
  const overlayLocalFrame = localFrame - overlay_start_offset_frames;
  const overlayTransInStyle = applyTransitionIn(
    overlay_transition_in?.type || 'fade',
    overlayLocalFrame,
    overlay_transition_in?.duration_frames || 10,
    width,
    height
  );
  const overlayTransOutStyle = applyTransitionOut(
    overlay_transition_out?.type || 'fade',
    overlayLocalFrame,
    overlayDuration,
    overlay_transition_out?.duration_frames || 10,
    width,
    height
  );

  const overlayEffectiveOpacity =
    overlay_opacity *
    (overlayTransInStyle.opacity ?? 1) *
    (overlayTransOutStyle.opacity ?? 1);
  const overlayEffectiveScale =
    overlay_scale *
    (overlayTransInStyle.scale ?? 1) *
    (overlayTransOutStyle.scale ?? 1);

  // Calculate position styles for picture-in-picture modes
  const getOverlayPositionStyle = (): React.CSSProperties => {
    if (overlay_position === 'full') {
      return {
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
      };
    }

    // Picture-in-picture positioning
    const pipSize = 0.35; // 35% of screen size
    const padding = 24; // pixels from edge

    const baseStyle: React.CSSProperties = {
      position: 'absolute',
      width: `${pipSize * 100}%`,
      height: `${pipSize * 100}%`,
      borderRadius: 12,
      overflow: 'hidden',
      boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
    };

    switch (overlay_position) {
      case 'top-right':
        return { ...baseStyle, top: padding, right: padding };
      case 'bottom-right':
        return { ...baseStyle, bottom: padding, right: padding };
      case 'top-left':
        return { ...baseStyle, top: padding, left: padding };
      case 'bottom-left':
        return { ...baseStyle, bottom: padding, left: padding };
      default:
        return baseStyle;
    }
  };

  return (
    <Sequence from={startFrame} durationInFrames={durationFrames}>
      <div
        style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          opacity: mainOpacity,
          transform: `translate(${mainTranslateX}px, ${mainTranslateY}px) scale(${mainScale})`,
        }}
      >
        {/* Main video with audio */}
        <OffthreadVideo
          src={main_video.url}
          startFrom={Math.round(main_video.start_time * fps)}
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />

        {/* B-Roll overlay video (video only, no audio) */}
        {localFrame >= overlay_start_offset_frames && localFrame < overlayEndFrame && (
          <div
            style={{
              ...getOverlayPositionStyle(),
              opacity: overlayEffectiveOpacity,
              transform: `scale(${overlayEffectiveScale})`,
              transformOrigin: overlay_position === 'full' ? 'center' : getTransformOrigin(overlay_position),
            }}
          >
            <OffthreadVideo
              src={overlay_video.url}
              startFrom={Math.round(overlay_video.start_time * fps)}
              volume={0} // Mute the overlay video - main audio continues
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />
          </div>
        )}

        {/* Text overlay */}
        {overlay && (
          <TextOverlayComponent {...overlay} segmentStartFrame={startFrame} />
        )}
      </div>
    </Sequence>
  );
};

/**
 * Get transform origin based on PiP position for natural scaling
 */
function getTransformOrigin(
  position: 'full' | 'top-right' | 'bottom-right' | 'top-left' | 'bottom-left'
): string {
  switch (position) {
    case 'top-right':
      return 'top right';
    case 'bottom-right':
      return 'bottom right';
    case 'top-left':
      return 'top left';
    case 'bottom-left':
      return 'bottom left';
    default:
      return 'center';
  }
}
