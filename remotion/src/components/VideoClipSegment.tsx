import React from 'react';
import { OffthreadVideo, useVideoConfig, Sequence, useCurrentFrame, interpolate } from 'remotion';
import type { VideoClipSource, TextOverlay, Transition } from '../types';
import { TextOverlayComponent } from './TextOverlay';
import { applyTransitionIn, applyTransitionOut } from '../utils/transitions';

interface Props {
  source: VideoClipSource;
  startFrame: number;
  durationFrames: number;
  overlay?: TextOverlay | null;
  transitionIn?: Transition | null;
  transitionOut?: Transition | null;
}

export const VideoClipSegment: React.FC<Props> = ({
  source,
  startFrame,
  durationFrames,
  overlay,
  transitionIn,
  transitionOut,
}) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();

  // Calculate the start time in the source video
  const clipDuration = source.end_time - source.start_time;

  // Calculate transition styles
  const transitionInDuration = transitionIn?.duration_frames || 0;
  const transitionOutDuration = transitionOut?.duration_frames || 0;

  // Get transition styles
  const localFrame = frame - startFrame;
  const transInStyle = applyTransitionIn(
    transitionIn?.type || 'cut',
    localFrame,
    transitionInDuration,
    width,
    height
  );
  const transOutStyle = applyTransitionOut(
    transitionOut?.type || 'cut',
    localFrame,
    durationFrames,
    transitionOutDuration,
    width,
    height
  );

  // Combine transition styles
  const combinedOpacity = (transInStyle.opacity ?? 1) * (transOutStyle.opacity ?? 1);
  const combinedScale = (transInStyle.scale ?? 1) * (transOutStyle.scale ?? 1);
  const combinedTranslateX = (transInStyle.translateX ?? 0) + (transOutStyle.translateX ?? 0);
  const combinedTranslateY = (transInStyle.translateY ?? 0) + (transOutStyle.translateY ?? 0);

  return (
    <Sequence from={startFrame} durationInFrames={durationFrames}>
      <div
        style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          opacity: combinedOpacity,
          transform: `translate(${combinedTranslateX}px, ${combinedTranslateY}px) scale(${combinedScale})`,
        }}
      >
        <OffthreadVideo
          src={source.url}
          startFrom={Math.round(source.start_time * fps)}
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
};
