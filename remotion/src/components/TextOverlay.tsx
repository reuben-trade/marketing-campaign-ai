import React from 'react';
import { interpolate, useCurrentFrame, spring, useVideoConfig } from 'remotion';
import type { TextOverlay as TextOverlayProps, TextAnimation, TextPosition } from '../types';

interface Props extends TextOverlayProps {
  segmentStartFrame: number;
}

const getPositionStyles = (position: TextPosition): React.CSSProperties => {
  const base: React.CSSProperties = {
    position: 'absolute',
    left: 0,
    right: 0,
    display: 'flex',
    justifyContent: 'center',
    padding: '0 24px',
  };

  switch (position) {
    case 'top':
      return { ...base, top: 60 };
    case 'center':
      return { ...base, top: '50%', transform: 'translateY(-50%)' };
    case 'bottom':
      return { ...base, bottom: 60 };
    case 'lower-third':
      return { ...base, bottom: '20%' };
    default:
      return { ...base, bottom: 60 };
  }
};

export const TextOverlayComponent: React.FC<Props> = ({
  text,
  position = 'center',
  font_size = 48,
  font_weight = 'bold',
  color = '#FFFFFF',
  background = 'rgba(0,0,0,0.5)',
  animation = 'none',
  segmentStartFrame,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Calculate frame relative to segment start
  const localFrame = frame - segmentStartFrame;
  const animationDuration = fps * 0.5; // 0.5 second animation

  let opacity = 1;
  let translateY = 0;
  let scale = 1;

  // Apply animation based on type
  switch (animation) {
    case 'fade_in':
      opacity = interpolate(localFrame, [0, animationDuration], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
      break;

    case 'pop_in':
      scale = spring({
        frame: localFrame,
        fps,
        config: {
          damping: 12,
          stiffness: 200,
          mass: 0.5,
        },
      });
      opacity = interpolate(localFrame, [0, 5], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
      break;

    case 'slide_up':
      translateY = interpolate(localFrame, [0, animationDuration], [50, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
      opacity = interpolate(localFrame, [0, animationDuration], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
      break;

    case 'typewriter':
      // Show characters progressively
      const charsToShow = Math.floor(
        interpolate(localFrame, [0, animationDuration * 2], [0, text.length], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      );
      return (
        <div style={getPositionStyles(position)}>
          <div
            style={{
              backgroundColor: background || 'transparent',
              padding: '12px 24px',
              borderRadius: 8,
            }}
          >
            <span
              style={{
                fontSize: font_size,
                fontWeight: font_weight as React.CSSProperties['fontWeight'],
                color,
                fontFamily: 'Inter, sans-serif',
                textAlign: 'center',
              }}
            >
              {text.slice(0, charsToShow)}
              <span style={{ opacity: 0.3 }}>|</span>
            </span>
          </div>
        </div>
      );

    case 'none':
    default:
      break;
  }

  return (
    <div style={getPositionStyles(position)}>
      <div
        style={{
          backgroundColor: background || 'transparent',
          padding: '12px 24px',
          borderRadius: 8,
          opacity,
          transform: `translateY(${translateY}px) scale(${scale})`,
        }}
      >
        <span
          style={{
            fontSize: font_size,
            fontWeight: font_weight as React.CSSProperties['fontWeight'],
            color,
            fontFamily: 'Inter, sans-serif',
            textAlign: 'center',
          }}
        >
          {text}
        </span>
      </div>
    </div>
  );
};
