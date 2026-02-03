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
  CaptionOverlay,
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
 *
 * Overlay support:
 * - caption_overlay: SRT-based captions synced to video clips (any segment type)
 */
export const BaseAdComposition: React.FC<Props> = ({
  timeline,
  brand_profile,
  audio_track,
  duration_in_frames,
}) => {
  const renderSegment = (segment: TimelineSegment) => {
    const commonProps = {
      startFrame: segment.start_frame,
      durationFrames: segment.duration_frames,
      overlay: segment.overlay,
      transitionIn: segment.transition_in,
      transitionOut: segment.transition_out,
      brandProfile: brand_profile,
    };

    let segmentElement: React.ReactNode = null;

    switch (segment.type) {
      case 'video_clip':
        if (!segment.source) {
          console.warn(`[BaseAdComposition] video_clip ${segment.id} missing source`);
        } else {
          segmentElement = (
            <VideoClipSegment
              key={`${segment.id}-video`}
              {...commonProps}
              source={segment.source}
            />
          );
        }
        break;

      case 'text_slide':
        if (!segment.text_content) {
          console.warn(`[BaseAdComposition] text_slide ${segment.id} missing text_content`);
        } else {
          segmentElement = (
            <TextSlideSegment
              key={`${segment.id}-text`}
              {...commonProps}
              content={segment.text_content}
            />
          );
        }
        break;

      case 'generated_broll':
        if (!segment.generated_source) {
          console.warn(`[BaseAdComposition] generated_broll ${segment.id} missing generated_source`);
        } else {
          segmentElement = (
            <BRollSegment
              key={`${segment.id}-broll`}
              {...commonProps}
              source={segment.generated_source}
            />
          );
        }
        break;

      case 'b_roll_overlay':
        if (!segment.broll_overlay_source) {
          console.warn(`[BaseAdComposition] b_roll_overlay ${segment.id} missing broll_overlay_source`);
        } else {
          segmentElement = (
            <BRollOverlay
              key={`${segment.id}-broll-overlay`}
              {...commonProps}
              source={segment.broll_overlay_source}
            />
          );
        }
        break;

      case 'title_card':
        if (!segment.title_card_content) {
          console.warn(`[BaseAdComposition] title_card ${segment.id} missing title_card_content`);
        } else {
          segmentElement = (
            <TitleCard
              key={`${segment.id}-title`}
              {...commonProps}
              content={segment.title_card_content}
            />
          );
        }
        break;

      case 'split_screen':
        if (!segment.split_screen_content) {
          console.warn(`[BaseAdComposition] split_screen ${segment.id} missing split_screen_content`);
        } else {
          segmentElement = (
            <SplitScreen
              key={`${segment.id}-split`}
              {...commonProps}
              content={segment.split_screen_content}
            />
          );
        }
        break;

      default:
        console.warn(`[BaseAdComposition] Unknown segment type: ${segment.type}`);
    }

    // If segment has caption overlay, render it alongside the segment
    if (segment.caption_overlay) {
      return (
        <React.Fragment key={segment.id}>
          {segmentElement}
          <CaptionOverlay
            key={`${segment.id}-caption`}
            config={segment.caption_overlay}
            startFrame={segment.start_frame}
            durationFrames={segment.duration_frames}
            brandProfile={brand_profile}
          />
        </React.Fragment>
      );
    }

    return segmentElement;
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
