import React from 'react';
import { Sequence, OffthreadVideo, useVideoConfig } from 'remotion';
import type { SplitScreenContent, BrandProfile } from '../types';

interface Props {
  content: SplitScreenContent;
  startFrame: number;
  durationFrames: number;
  brandProfile?: BrandProfile | null;
}

/**
 * SplitScreen component for side-by-side video comparisons.
 *
 * Features:
 * - Three layouts: horizontal (left/right), vertical (top/bottom), pip (picture-in-picture)
 * - Configurable split ratio
 * - Optional labels (e.g., "BEFORE" / "AFTER")
 * - Optional divider line
 * - Configurable audio source (left, right, or none)
 */
export const SplitScreen: React.FC<Props> = ({
  content,
  startFrame,
  durationFrames,
  brandProfile,
}) => {
  const { fps, width, height } = useVideoConfig();

  // Extract content with defaults
  const {
    layout,
    left_video,
    right_video,
    split_ratio = 0.5,
    left_label,
    right_label,
    label_font_size = 24,
    label_color = '#FFFFFF',
    label_background = 'rgba(0,0,0,0.6)',
    show_divider = false,
    divider_width = 4,
    divider_color = '#FFFFFF',
    audio_source = 'left',
    pip_position = 'bottom-right',
  } = content;

  const fontFamily = brandProfile?.font_family || 'Inter';

  // Calculate dimensions based on layout
  const getDimensions = () => {
    if (layout === 'horizontal') {
      const leftWidth = Math.round(width * split_ratio);
      const rightWidth = width - leftWidth;
      return {
        left: { width: leftWidth, height, top: 0, left: 0 },
        right: { width: rightWidth, height, top: 0, left: leftWidth },
        divider: {
          width: divider_width,
          height,
          top: 0,
          left: leftWidth - divider_width / 2,
        },
      };
    } else if (layout === 'vertical') {
      const topHeight = Math.round(height * split_ratio);
      const bottomHeight = height - topHeight;
      return {
        left: { width, height: topHeight, top: 0, left: 0 }, // "left" = top
        right: { width, height: bottomHeight, top: topHeight, left: 0 }, // "right" = bottom
        divider: {
          width,
          height: divider_width,
          top: topHeight - divider_width / 2,
          left: 0,
        },
      };
    } else {
      // PiP layout
      const pipSize = Math.min(width, height) * split_ratio * 0.6; // Overlay size
      const padding = 24;
      const pipDimensions = { width: pipSize, height: pipSize * (9 / 16) }; // 16:9 aspect

      let pipTop = 0;
      let pipLeft = 0;

      switch (pip_position) {
        case 'top-left':
          pipTop = padding;
          pipLeft = padding;
          break;
        case 'top-right':
          pipTop = padding;
          pipLeft = width - pipDimensions.width - padding;
          break;
        case 'bottom-left':
          pipTop = height - pipDimensions.height - padding;
          pipLeft = padding;
          break;
        case 'bottom-right':
        default:
          pipTop = height - pipDimensions.height - padding;
          pipLeft = width - pipDimensions.width - padding;
          break;
      }

      return {
        left: { width, height, top: 0, left: 0 }, // Main/background video
        right: {
          width: pipDimensions.width,
          height: pipDimensions.height,
          top: pipTop,
          left: pipLeft,
        }, // PiP overlay
        divider: null, // No divider for PiP
      };
    }
  };

  const dimensions = getDimensions();

  // Render a label overlay
  const renderLabel = (
    label: string | null | undefined,
    position: 'left' | 'right',
    dims: { width: number; height: number; top: number; left: number }
  ) => {
    if (!label) return null;

    return (
      <div
        style={{
          position: 'absolute',
          top: dims.top + 16,
          left: dims.left + (layout === 'horizontal' || layout === 'pip' ? 16 : dims.width / 2),
          transform: layout === 'vertical' ? 'translateX(-50%)' : 'none',
          backgroundColor: label_background || 'transparent',
          padding: '8px 16px',
          borderRadius: 4,
          zIndex: 10,
        }}
      >
        <span
          style={{
            fontSize: label_font_size,
            fontFamily: `${fontFamily}, sans-serif`,
            fontWeight: 'bold',
            color: label_color,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}
        >
          {label}
        </span>
      </div>
    );
  };

  // Render a video panel
  const renderVideoPanel = (
    video: typeof left_video,
    dims: { width: number; height: number; top: number; left: number },
    muted: boolean,
    isPip: boolean = false
  ) => {
    return (
      <div
        style={{
          position: 'absolute',
          top: dims.top,
          left: dims.left,
          width: dims.width,
          height: dims.height,
          overflow: 'hidden',
          borderRadius: isPip ? 8 : 0,
          boxShadow: isPip ? '0 4px 20px rgba(0,0,0,0.4)' : 'none',
        }}
      >
        <OffthreadVideo
          src={video.url}
          startFrom={Math.round(video.start_time * fps)}
          endAt={Math.round(video.end_time * fps)}
          muted={muted}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
      </div>
    );
  };

  // Render divider line
  const renderDivider = () => {
    if (!show_divider || !dimensions.divider) return null;

    return (
      <div
        style={{
          position: 'absolute',
          top: dimensions.divider.top,
          left: dimensions.divider.left,
          width: dimensions.divider.width,
          height: dimensions.divider.height,
          backgroundColor: divider_color,
          zIndex: 5,
        }}
      />
    );
  };

  return (
    <Sequence from={startFrame} durationInFrames={durationFrames}>
      <div
        style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          backgroundColor: '#000000',
        }}
      >
        {/* Left/Main video */}
        {renderVideoPanel(
          left_video,
          dimensions.left,
          audio_source !== 'left',
          false
        )}

        {/* Right/Overlay video */}
        {renderVideoPanel(
          right_video,
          dimensions.right,
          audio_source !== 'right',
          layout === 'pip'
        )}

        {/* Divider */}
        {renderDivider()}

        {/* Labels */}
        {renderLabel(left_label, 'left', dimensions.left)}
        {renderLabel(right_label, 'right', dimensions.right)}

        {/* PiP border */}
        {layout === 'pip' && (
          <div
            style={{
              position: 'absolute',
              top: dimensions.right.top - 2,
              left: dimensions.right.left - 2,
              width: dimensions.right.width + 4,
              height: dimensions.right.height + 4,
              border: `2px solid ${brandProfile?.primary_color || '#FFFFFF'}`,
              borderRadius: 10,
              pointerEvents: 'none',
              zIndex: 15,
            }}
          />
        )}
      </div>
    </Sequence>
  );
};
