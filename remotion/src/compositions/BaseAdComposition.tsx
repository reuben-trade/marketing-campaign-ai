import React from 'react';
import { AbsoluteFill } from 'remotion';
import type { AdCompositionProps, TimelineSegment } from '../types';
import {
  VideoClipSegment,
  TextSlideSegment,
  BRollSegment,
  AudioTrackComponent,
} from '../components';

interface Props extends AdCompositionProps {}

/**
 * Base ad composition that renders the timeline segments.
 * Used by all aspect ratio compositions (vertical, horizontal, square).
 */
export const BaseAdComposition: React.FC<Props> = ({
  timeline,
  brand_profile,
  audio_track,
  duration_in_frames,
}) => {
  const renderSegment = (segment: TimelineSegment) => {
    const commonProps = {
      key: segment.id,
      startFrame: segment.start_frame,
      durationFrames: segment.duration_frames,
      overlay: segment.overlay,
      transitionIn: segment.transition_in,
      transitionOut: segment.transition_out,
      brandProfile: brand_profile,
    };

    switch (segment.type) {
      case 'video_clip':
        if (!segment.source) {
          console.warn(`Video clip segment ${segment.id} missing source`);
          return null;
        }
        return (
          <VideoClipSegment
            {...commonProps}
            source={segment.source}
          />
        );

      case 'text_slide':
        if (!segment.text_content) {
          console.warn(`Text slide segment ${segment.id} missing text_content`);
          return null;
        }
        return (
          <TextSlideSegment
            {...commonProps}
            content={segment.text_content}
          />
        );

      case 'generated_broll':
        if (!segment.generated_source) {
          console.warn(`B-roll segment ${segment.id} missing generated_source`);
          return null;
        }
        return (
          <BRollSegment
            {...commonProps}
            source={segment.generated_source}
          />
        );

      default:
        console.warn(`Unknown segment type: ${segment.type}`);
        return null;
    }
  };

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000' }}>
      {/* Render all timeline segments */}
      {timeline.map(renderSegment)}

      {/* Background audio track */}
      {audio_track && (
        <AudioTrackComponent
          {...audio_track}
          totalDurationFrames={duration_in_frames}
        />
      )}
    </AbsoluteFill>
  );
};
