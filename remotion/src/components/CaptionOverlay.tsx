import React, { useMemo } from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, Easing } from 'remotion';
import { parseSrt } from '@remotion/captions';
import type { CaptionOverlayConfig, BrandProfile } from '../types';

interface Props {
  config: CaptionOverlayConfig;
  startFrame: number;
  durationFrames: number;
  brandProfile?: BrandProfile | null;
}

// Regex to match speaker tags like [Speaker 1]: or [Speaker X]:
const SPEAKER_TAG_REGEX = /^\[Speaker\s*\d*\]:\s*/i;

/**
 * Parse speaker tag from caption text.
 * Returns { speaker: string | null, text: string }
 */
function parseSpeakerTag(text: string): { speaker: string | null; text: string } {
  const match = text.match(SPEAKER_TAG_REGEX);
  if (match) {
    return {
      speaker: match[0].replace(/[[\]:]/g, '').trim(),
      text: text.slice(match[0].length),
    };
  }
  return { speaker: null, text };
}

/**
 * CaptionOverlay component for displaying SRT captions synced to video clips.
 *
 * Features:
 * - Parses SRT content using @remotion/captions
 * - Filters cues by clip time range
 * - Offsets timestamps to timeline position
 * - Handles speaker tags (strip or style)
 * - Multiple display styles: minimal, bar, karaoke
 */
export const CaptionOverlay: React.FC<Props> = ({
  config,
  startFrame,
  durationFrames,
  brandProfile,
}) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const localFrame = frame - startFrame;

  // Extract config with defaults
  const {
    srt_content,
    clip_timestamp_start,
    clip_timestamp_end,
    style = 'minimal',
    position = 'bottom',
    speaker_tag_style = 'hidden',
    font_size = 48,
    font_family,
    text_color = '#FFFFFF',
    background_color = '#000000',
    background_opacity = 0.7,
  } = config;

  const fontFamilyToUse = font_family || brandProfile?.font_family || 'Inter';

  // Parse SRT and filter/transform cues (memoized)
  const processedCues = useMemo(() => {
    if (!srt_content) return [];

    try {
      const { captions } = parseSrt({ input: srt_content });

      // Convert clip timestamps to milliseconds for comparison
      const clipStartMs = clip_timestamp_start * 1000;
      const clipEndMs = clip_timestamp_end * 1000;

      // Filter cues that fall within the clip range
      // A cue is included if its start time falls within the clip range
      const filteredCues = captions.filter(
        (cue) => cue.startMs >= clipStartMs && cue.startMs < clipEndMs
      );

      // Transform timestamps: offset to timeline position
      // displayTimeMs = (cue.startMs - clipStartMs) + (timelinePositionInSeconds * 1000)
      // But since we're using frames, we calculate display frame instead
      return filteredCues.map((cue) => {
        const offsetFromClipStart = cue.startMs - clipStartMs;
        const displayStartFrame = Math.round((offsetFromClipStart / 1000) * fps);
        const displayEndFrame = Math.round(((cue.endMs - clipStartMs) / 1000) * fps);

        // Parse speaker tag
        const { speaker, text } = parseSpeakerTag(cue.text);

        return {
          ...cue,
          displayStartFrame,
          displayEndFrame,
          speaker,
          cleanText: text,
        };
      });
    } catch (error) {
      console.error('Failed to parse SRT content:', error);
      return [];
    }
  }, [srt_content, clip_timestamp_start, clip_timestamp_end, fps]);

  // Find the currently active cue
  const activeCue = useMemo(() => {
    return processedCues.find(
      (cue) => localFrame >= cue.displayStartFrame && localFrame < cue.displayEndFrame
    );
  }, [processedCues, localFrame]);

  // Get position styles based on position prop
  const getPositionStyles = (): React.CSSProperties => {
    const padding = Math.min(width * 0.05, 48);
    switch (position) {
      case 'top':
        return {
          top: padding,
          left: padding,
          right: padding,
        };
      case 'center':
        return {
          top: '50%',
          left: padding,
          right: padding,
          transform: 'translateY(-50%)',
        };
      case 'bottom':
      default:
        return {
          bottom: padding + 60, // Leave room for safe area
          left: padding,
          right: padding,
        };
    }
  };

  // Get style-specific container styles
  const getStyleContainerStyles = (): React.CSSProperties => {
    switch (style) {
      case 'bar':
        return {
          backgroundColor: `rgba(${hexToRgb(background_color)}, ${background_opacity})`,
          padding: '16px 24px',
          borderRadius: 8,
        };
      case 'karaoke':
        return {
          padding: '16px 24px',
        };
      case 'minimal':
      default:
        return {
          padding: '8px 16px',
        };
    }
  };

  // Render caption text with optional speaker tag
  const renderCaptionText = (cue: typeof processedCues[0]) => {
    const { speaker, cleanText } = cue;

    // Calculate progress for karaoke animation
    const cueProgress =
      style === 'karaoke' && cue.displayEndFrame > cue.displayStartFrame
        ? (localFrame - cue.displayStartFrame) / (cue.displayEndFrame - cue.displayStartFrame)
        : 1;

    // For karaoke, split into words and highlight progressively
    if (style === 'karaoke') {
      const words = cleanText.split(' ');
      const highlightUpTo = Math.floor(cueProgress * words.length);

      return (
        <span>
          {speaker_tag_style !== 'hidden' && speaker && (
            <span
              style={{
                opacity: speaker_tag_style === 'dimmed' ? 0.5 : 1,
                color: speaker_tag_style === 'colored' ? brandProfile?.primary_color || '#FFD700' : text_color,
                marginRight: 8,
              }}
            >
              {speaker}:
            </span>
          )}
          {words.map((word, idx) => (
            <span
              key={idx}
              style={{
                display: 'inline-block',
                marginRight: 8,
                opacity: idx < highlightUpTo ? 1 : 0.4,
                fontWeight: idx < highlightUpTo ? 'bold' : 'normal',
                transition: 'opacity 0.1s, font-weight 0.1s',
              }}
            >
              {word}
            </span>
          ))}
        </span>
      );
    }

    // Non-karaoke styles: show full text
    return (
      <span>
        {speaker_tag_style !== 'hidden' && speaker && (
          <span
            style={{
              opacity: speaker_tag_style === 'dimmed' ? 0.5 : 1,
              color: speaker_tag_style === 'colored' ? brandProfile?.primary_color || '#FFD700' : text_color,
              marginRight: 8,
            }}
          >
            {speaker}:
          </span>
        )}
        {cleanText}
      </span>
    );
  };

  // Early return if nothing to display
  if (localFrame < 0 || localFrame >= durationFrames) {
    return null;
  }

  if (!activeCue) {
    return null;
  }

  // Entry/exit animation for the caption
  const cueLocalFrame = localFrame - activeCue.displayStartFrame;
  const cueDuration = activeCue.displayEndFrame - activeCue.displayStartFrame;

  const entryProgress = interpolate(cueLocalFrame, [0, 5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const exitFrameStart = cueDuration - 5;
  const exitProgress =
    cueLocalFrame > exitFrameStart
      ? interpolate(cueLocalFrame, [exitFrameStart, cueDuration], [1, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.in(Easing.cubic),
        })
      : 1;

  const overallOpacity = entryProgress * exitProgress;

  return (
    <div
      style={{
        position: 'absolute',
        ...getPositionStyles(),
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        opacity: overallOpacity,
        pointerEvents: 'none',
        zIndex: 100,
      }}
    >
      <div
        style={{
          fontSize: font_size,
          fontFamily: `${fontFamilyToUse}, sans-serif`,
          lineHeight: 1.4,
          maxWidth: '100%',
          color: text_color,
          textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
          textAlign: 'center',
          whiteSpace: 'pre-wrap', // Preserve spaces as recommended by @remotion/captions
          ...getStyleContainerStyles(),
        }}
      >
        {renderCaptionText(activeCue)}
      </div>
    </div>
  );
};

// Helper: Convert hex color to RGB values
function hexToRgb(hex: string): string {
  const cleanHex = hex.replace('#', '');
  const bigint = parseInt(cleanHex, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `${r}, ${g}, ${b}`;
}
