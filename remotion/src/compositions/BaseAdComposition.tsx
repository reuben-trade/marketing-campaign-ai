import React from 'react';
import { AbsoluteFill } from 'remotion';
import type { AdCompositionProps, TimelineSegment } from '../types';
import {
  VideoClipSegment,
  TextSlideSegment,
  BRollSegment,
  BRollOverlay,
  TitleCard,
  SplitScreen,
  AudioTrackComponent,
} from '../components';

interface Props extends AdCompositionProps {}

/**
 * Base ad composition that renders the timeline segments.
 * Used by all aspect ratio compositions (vertical, horizontal, square).
 *
 * Supports segment types:
 * - video_clip: Main footage with time slicing
 * - text_slide: Clean text with spring animations
 * - generated_broll: AI-generated B-Roll (Veo 2)
 * - b_roll_overlay: J-cut/L-cut with audio continuity
 * - title_card: Animated title screen with branding
 * - split_screen: Side-by-side video comparison
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
          console.warn(`[BaseAdComposition] video_clip ${segment.id} missing source`);
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
          console.warn(`[BaseAdComposition] text_slide ${segment.id} missing text_content`);
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
          console.warn(`[BaseAdComposition] generated_broll ${segment.id} missing generated_source`);
          return null;
        }
        return (
          <BRollSegment
            {...commonProps}
            source={segment.generated_source}
          />
        );

      case 'b_roll_overlay':
        if (!segment.broll_overlay_source) {
          console.warn(`[BaseAdComposition] b_roll_overlay ${segment.id} missing broll_overlay_source`);
          return null;
        }
        return (
          <BRollOverlay
            {...commonProps}
            source={segment.broll_overlay_source}
          />
        );

      case 'title_card':
        if (!segment.title_card_content) {
          console.warn(`[BaseAdComposition] title_card ${segment.id} missing title_card_content`);
          return null;
        }
        return (
          <TitleCard
            {...commonProps}
            content={segment.title_card_content}
          />
        );

      case 'split_screen':
        if (!segment.split_screen_content) {
          console.warn(`[BaseAdComposition] split_screen ${segment.id} missing split_screen_content`);
          return null;
        }
        return (
          <SplitScreen
            {...commonProps}
            content={segment.split_screen_content}
          />
        );

      default:
        console.warn(`[BaseAdComposition] Unknown segment type: ${segment.type}`);
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
