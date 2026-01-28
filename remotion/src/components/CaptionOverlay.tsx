import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, Easing, spring } from 'remotion';
import type {
  CaptionOverlayConfig,
  CaptionEntry,
  TranscriptWord,
  CaptionStyle,
  CaptionPosition,
  BrandProfile,
} from '../types';

interface Props {
  config: CaptionOverlayConfig;
  startFrame: number;
  durationFrames: number;
  brandProfile?: BrandProfile | null;
  // Video start time in seconds (for syncing with transcript timestamps)
  videoStartTime?: number;
}

/**
 * CaptionOverlay component for timestamped captions synced to transcript_words.
 *
 * Features:
 * - Word-level sync with transcript_words data
 * - Power word highlighting
 * - Multiple styles: minimal, bar, karaoke
 * - Smooth word-by-word animation
 * - Support for grouped caption entries
 */
export const CaptionOverlay: React.FC<Props> = ({
  config,
  startFrame,
  durationFrames,
  brandProfile,
  videoStartTime = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const localFrame = frame - startFrame;

  // Extract config with defaults
  const {
    captions,
    transcript_words,
    style = 'minimal',
    position = 'bottom',
    max_words_per_line = 5,
    font_size = 48,
    font_family,
    text_color = '#FFFFFF',
    highlight_color = '#FFD700',
    background_color = '#000000',
    background_opacity = 0.7,
    word_animation = 'pop',
    power_words = [],
  } = config;

  const fontFamilyToUse = font_family || brandProfile?.font_family || 'Inter';
  const highlightColorToUse = highlight_color || brandProfile?.primary_color || '#FFD700';

  // Calculate current time in seconds relative to video
  const currentTimeInSegment = localFrame / fps;
  const currentVideoTime = videoStartTime + currentTimeInSegment;

  // Check if a word should be highlighted (power word)
  const isHighlightWord = (word: string): boolean => {
    const normalizedWord = word.toLowerCase().replace(/[^\w]/g, '');
    const allPowerWords = [...(power_words || [])];

    // Add per-caption highlight words if using captions
    if (captions) {
      captions.forEach((cap) => {
        if (cap.highlight_words) {
          allPowerWords.push(...cap.highlight_words);
        }
      });
    }

    return allPowerWords.some(
      (pw) => pw.toLowerCase() === normalizedWord
    );
  };

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

  // Render word with animation
  const renderWord = (
    word: string,
    wordStartTime: number,
    wordEndTime: number,
    index: number,
    isActive: boolean,
    isPast: boolean
  ): React.ReactNode => {
    const isHighlight = isHighlightWord(word);
    const wordLocalStartFrame = (wordStartTime - videoStartTime) * fps;
    const wordProgress = Math.max(0, localFrame - wordLocalStartFrame);

    // Animation based on word_animation setting
    let animStyle: React.CSSProperties = {};
    if (isActive && word_animation !== 'none') {
      if (word_animation === 'pop') {
        const scale = spring({
          frame: wordProgress,
          fps,
          config: {
            damping: 12,
            stiffness: 200,
            mass: 0.3,
          },
        });
        animStyle = { transform: `scale(${scale})` };
      } else if (word_animation === 'fade') {
        const opacity = interpolate(wordProgress, [0, 5], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        animStyle = { opacity };
      }
    }

    // Karaoke style: highlight the active word
    const isKaraokeActive = style === 'karaoke' && isActive;

    return (
      <span
        key={`${word}-${index}`}
        style={{
          display: 'inline-block',
          marginRight: 8,
          color: isHighlight ? highlightColorToUse : text_color,
          fontWeight: isHighlight || isKaraokeActive ? 'bold' : 'normal',
          textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
          ...(isKaraokeActive && {
            backgroundColor: highlightColorToUse,
            color: '#000000',
            padding: '2px 8px',
            borderRadius: 4,
          }),
          ...(style === 'karaoke' && isPast && !isActive && {
            opacity: 0.6,
          }),
          ...animStyle,
        }}
      >
        {word}
      </span>
    );
  };

  // Render captions based on mode (transcript_words or captions)
  const renderCaptions = () => {
    // Mode 1: Word-level sync with transcript_words
    if (transcript_words && transcript_words.length > 0) {
      return renderTranscriptWords(transcript_words);
    }

    // Mode 2: Caption entries
    if (captions && captions.length > 0) {
      return renderCaptionEntries(captions);
    }

    return null;
  };

  // Render word-level synced captions from transcript_words
  const renderTranscriptWords = (words: TranscriptWord[]) => {
    // Find which words are currently visible
    const visibleWords: Array<{
      word: TranscriptWord;
      isActive: boolean;
      isPast: boolean;
    }> = [];

    // Find current and recent words (window of max_words_per_line * 2)
    const windowSize = max_words_per_line * 2;
    let activeIndex = -1;

    // Find the active word
    for (let i = 0; i < words.length; i++) {
      const w = words[i];
      if (currentVideoTime >= w.start && currentVideoTime < w.end) {
        activeIndex = i;
        break;
      }
      // If we're between words, attach to the next one
      if (i < words.length - 1 && currentVideoTime >= w.end && currentVideoTime < words[i + 1].start) {
        activeIndex = i;
        break;
      }
    }

    // If no active word found, check if we're past all words
    if (activeIndex === -1 && words.length > 0) {
      if (currentVideoTime >= words[words.length - 1].end) {
        activeIndex = words.length - 1;
      } else if (currentVideoTime < words[0].start) {
        // Not started yet
        return null;
      }
    }

    if (activeIndex === -1) return null;

    // Calculate window around active word
    const startIdx = Math.max(0, activeIndex - Math.floor(max_words_per_line / 2));
    const endIdx = Math.min(words.length, startIdx + windowSize);

    for (let i = startIdx; i < endIdx; i++) {
      const w = words[i];
      const isActive = currentVideoTime >= w.start && currentVideoTime < w.end;
      const isPast = currentVideoTime >= w.end;
      visibleWords.push({ word: w, isActive, isPast });
    }

    // Group into lines
    const lines: Array<Array<typeof visibleWords[0]>> = [];
    for (let i = 0; i < visibleWords.length; i += max_words_per_line) {
      lines.push(visibleWords.slice(i, i + max_words_per_line));
    }

    return (
      <div style={{ textAlign: 'center' }}>
        {lines.map((line, lineIdx) => (
          <div key={lineIdx} style={{ marginBottom: 8 }}>
            {line.map((item, wordIdx) =>
              renderWord(
                item.word.word,
                item.word.start,
                item.word.end,
                lineIdx * max_words_per_line + wordIdx,
                item.isActive,
                item.isPast
              )
            )}
          </div>
        ))}
      </div>
    );
  };

  // Render caption entries (sentence-level)
  const renderCaptionEntries = (entries: CaptionEntry[]) => {
    // Find the currently active caption
    const activeCaption = entries.find(
      (cap) => currentVideoTime >= cap.start_time && currentVideoTime < cap.end_time
    );

    if (!activeCaption) return null;

    // Calculate progress within caption for animation
    const captionDuration = activeCaption.end_time - activeCaption.start_time;
    const captionProgress = (currentVideoTime - activeCaption.start_time) / captionDuration;

    // Split text into words for highlighting
    const words = activeCaption.text.split(' ');
    const highlightSet = new Set(
      [...(activeCaption.highlight_words || []), ...(power_words || [])].map((w) =>
        w.toLowerCase()
      )
    );

    // For karaoke style, determine which word should be highlighted based on progress
    const karaokeActiveIdx = style === 'karaoke'
      ? Math.min(Math.floor(captionProgress * words.length), words.length - 1)
      : -1;

    return (
      <div style={{ textAlign: 'center' }}>
        {words.map((word, idx) => {
          const cleanWord = word.toLowerCase().replace(/[^\w]/g, '');
          const isHighlight = highlightSet.has(cleanWord);
          const isKaraokeActive = idx === karaokeActiveIdx;

          return (
            <span
              key={`${word}-${idx}`}
              style={{
                display: 'inline-block',
                marginRight: 8,
                color: isHighlight ? highlightColorToUse : text_color,
                fontWeight: isHighlight || isKaraokeActive ? 'bold' : 'normal',
                textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
                ...(isKaraokeActive && style === 'karaoke' && {
                  backgroundColor: highlightColorToUse,
                  color: '#000000',
                  padding: '2px 8px',
                  borderRadius: 4,
                }),
                ...(style === 'karaoke' && idx < karaokeActiveIdx && {
                  opacity: 0.6,
                }),
              }}
            >
              {word}
            </span>
          );
        })}
      </div>
    );
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

  // Early return if nothing to display
  if (localFrame < 0 || localFrame >= durationFrames) {
    return null;
  }

  const captionContent = renderCaptions();
  if (!captionContent) return null;

  // Entry animation
  const entryProgress = interpolate(localFrame, [0, 10], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  // Exit animation
  const exitFrameStart = durationFrames - 10;
  const exitProgress = localFrame > exitFrameStart
    ? interpolate(localFrame, [exitFrameStart, durationFrames], [1, 0], {
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
          ...getStyleContainerStyles(),
        }}
      >
        {captionContent}
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
