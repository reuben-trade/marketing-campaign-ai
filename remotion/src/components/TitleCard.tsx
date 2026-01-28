import React from 'react';
import {
  Sequence,
  useCurrentFrame,
  spring,
  useVideoConfig,
  interpolate,
  Easing,
} from 'remotion';
import type {
  BrandProfile,
  Transition,
  TitleCardContent,
  TitleAnimation,
} from '../types';
import { applyTransitionIn, applyTransitionOut } from '../utils/transitions';

interface Props {
  content: TitleCardContent;
  startFrame: number;
  durationFrames: number;
  brandProfile?: BrandProfile | null;
  transitionIn?: Transition | null;
  transitionOut?: Transition | null;
}

/**
 * TitleCard component for animated title screens with branding support.
 *
 * Features:
 * - Animated headline and subheadline with multiple animation styles
 * - Brand color and font integration
 * - Optional logo placement (top, bottom, or behind text)
 * - Gradient and image backgrounds
 * - Multiple layout options (centered, left, right, stacked)
 */
export const TitleCard: React.FC<Props> = ({
  content,
  startFrame,
  durationFrames,
  brandProfile,
  transitionIn,
  transitionOut,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const localFrame = frame - startFrame;

  // Extract content with defaults
  const {
    headline,
    subheadline,
    tagline,
    background_color,
    text_color = '#FFFFFF',
    accent_color,
    animation = 'fade_up',
    layout = 'centered',
    show_logo = true,
    logo_position = 'bottom',
    background_gradient,
    background_image_url,
    background_image_opacity = 0.3,
  } = content;

  // Use brand profile colors as fallbacks
  const bgColor = background_color || brandProfile?.primary_color || '#1a1a2e';
  const accentColor = accent_color || brandProfile?.primary_color || '#FF5733';
  const fontFamily = brandProfile?.font_family || 'Inter';

  // Calculate background style
  const getBackgroundStyle = (): React.CSSProperties => {
    if (background_gradient) {
      const angle = background_gradient.angle ?? 135;
      return {
        background: `linear-gradient(${angle}deg, ${background_gradient.start_color}, ${background_gradient.end_color})`,
      };
    }
    return {
      backgroundColor: bgColor,
    };
  };

  // Animation helpers
  const getAnimationStyle = (
    animType: TitleAnimation,
    localFrame: number,
    delay: number = 0
  ): React.CSSProperties => {
    const adjustedFrame = localFrame - delay;

    if (adjustedFrame < 0) {
      return { opacity: 0 };
    }

    switch (animType) {
      case 'fade_up': {
        const opacity = interpolate(adjustedFrame, [0, 15], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        const translateY = interpolate(adjustedFrame, [0, 20], [40, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.out(Easing.cubic),
        });
        return {
          opacity,
          transform: `translateY(${translateY}px)`,
        };
      }

      case 'fade_down': {
        const opacity = interpolate(adjustedFrame, [0, 15], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        const translateY = interpolate(adjustedFrame, [0, 20], [-40, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.out(Easing.cubic),
        });
        return {
          opacity,
          transform: `translateY(${translateY}px)`,
        };
      }

      case 'scale_in': {
        const scale = spring({
          frame: adjustedFrame,
          fps,
          config: {
            damping: 12,
            stiffness: 200,
            mass: 0.5,
          },
        });
        const opacity = interpolate(adjustedFrame, [0, 10], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        return {
          opacity,
          transform: `scale(${scale})`,
        };
      }

      case 'slide_left': {
        const opacity = interpolate(adjustedFrame, [0, 15], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        const translateX = interpolate(adjustedFrame, [0, 20], [100, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.out(Easing.cubic),
        });
        return {
          opacity,
          transform: `translateX(${translateX}px)`,
        };
      }

      case 'slide_right': {
        const opacity = interpolate(adjustedFrame, [0, 15], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        const translateX = interpolate(adjustedFrame, [0, 20], [-100, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.out(Easing.cubic),
        });
        return {
          opacity,
          transform: `translateX(${translateX}px)`,
        };
      }

      case 'typewriter': {
        // For typewriter, we handle it differently - return full opacity
        // The actual typewriter effect is handled in the text rendering
        const opacity = interpolate(adjustedFrame, [0, 5], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        return { opacity };
      }

      case 'none':
      default:
        return { opacity: 1 };
    }
  };

  // Typewriter text renderer
  const renderTypewriterText = (
    text: string,
    adjustedFrame: number,
    charsPerFrame: number = 0.5
  ): string => {
    if (adjustedFrame < 0) return '';
    const charsToShow = Math.floor(adjustedFrame * charsPerFrame);
    return text.substring(0, Math.min(charsToShow, text.length));
  };

  // Get layout alignment
  const getLayoutStyle = (): React.CSSProperties => {
    switch (layout) {
      case 'left_aligned':
        return {
          alignItems: 'flex-start',
          textAlign: 'left',
          paddingLeft: 80,
          paddingRight: 48,
        };
      case 'right_aligned':
        return {
          alignItems: 'flex-end',
          textAlign: 'right',
          paddingLeft: 48,
          paddingRight: 80,
        };
      case 'stacked':
        return {
          alignItems: 'center',
          textAlign: 'center',
          justifyContent: 'flex-end',
          paddingBottom: 120,
        };
      case 'centered':
      default:
        return {
          alignItems: 'center',
          textAlign: 'center',
        };
    }
  };

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
  const combinedScale = (transInStyle.scale ?? 1) * (transOutStyle.scale ?? 1);
  const combinedTranslateX = (transInStyle.translateX ?? 0) + (transOutStyle.translateX ?? 0);
  const combinedTranslateY = (transInStyle.translateY ?? 0) + (transOutStyle.translateY ?? 0);

  // Animation delays
  const headlineDelay = 5;
  const subheadlineDelay = 15;
  const taglineDelay = 25;

  // Determine if using typewriter effect
  const isTypewriter = animation === 'typewriter';

  return (
    <Sequence from={startFrame} durationInFrames={durationFrames}>
      <div
        style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          ...getBackgroundStyle(),
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: 48,
          opacity: combinedOpacity,
          transform: `translate(${combinedTranslateX}px, ${combinedTranslateY}px) scale(${combinedScale})`,
          ...getLayoutStyle(),
        }}
      >
        {/* Background image overlay */}
        {background_image_url && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              backgroundImage: `url(${background_image_url})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              opacity: background_image_opacity,
            }}
          />
        )}

        {/* Logo behind text */}
        {show_logo && logo_position === 'behind' && brandProfile?.logo_url && (
          <img
            src={brandProfile.logo_url}
            alt="Brand logo"
            style={{
              position: 'absolute',
              maxHeight: '40%',
              maxWidth: '60%',
              objectFit: 'contain',
              opacity: 0.15,
              filter: 'grayscale(100%)',
            }}
          />
        )}

        {/* Logo at top */}
        {show_logo && logo_position === 'top' && brandProfile?.logo_url && (
          <img
            src={brandProfile.logo_url}
            alt="Brand logo"
            style={{
              position: 'absolute',
              top: 48,
              maxHeight: 60,
              maxWidth: 160,
              objectFit: 'contain',
              ...getAnimationStyle(animation, localFrame, 0),
            }}
          />
        )}

        {/* Main content container */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
            zIndex: 1,
            maxWidth: '90%',
          }}
        >
          {/* Headline */}
          <h1
            style={{
              fontSize: Math.min(width * 0.08, 96),
              fontWeight: 'bold',
              color: text_color,
              fontFamily: `${fontFamily}, sans-serif`,
              margin: 0,
              lineHeight: 1.1,
              letterSpacing: '-0.02em',
              ...getAnimationStyle(animation, localFrame, headlineDelay),
            }}
          >
            {isTypewriter
              ? renderTypewriterText(headline, localFrame - headlineDelay, 1)
              : headline}
            {isTypewriter && localFrame >= headlineDelay && (
              <span
                style={{
                  opacity: Math.sin(localFrame * 0.3) > 0 ? 1 : 0,
                  marginLeft: 2,
                }}
              >
                |
              </span>
            )}
          </h1>

          {/* Subheadline */}
          {subheadline && (
            <h2
              style={{
                fontSize: Math.min(width * 0.045, 48),
                fontWeight: 'normal',
                color: text_color,
                fontFamily: `${fontFamily}, sans-serif`,
                margin: 0,
                lineHeight: 1.3,
                opacity: 0.9,
                ...getAnimationStyle(animation, localFrame, subheadlineDelay),
              }}
            >
              {isTypewriter
                ? renderTypewriterText(
                    subheadline,
                    localFrame - subheadlineDelay - headline.length,
                    1
                  )
                : subheadline}
            </h2>
          )}

          {/* Tagline with accent */}
          {tagline && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                marginTop: 8,
                ...getAnimationStyle(animation, localFrame, taglineDelay),
              }}
            >
              {/* Accent line */}
              <div
                style={{
                  width: 40,
                  height: 4,
                  backgroundColor: accentColor,
                  borderRadius: 2,
                }}
              />
              <span
                style={{
                  fontSize: Math.min(width * 0.03, 28),
                  fontWeight: '500',
                  color: accentColor,
                  fontFamily: `${fontFamily}, sans-serif`,
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                }}
              >
                {tagline}
              </span>
            </div>
          )}
        </div>

        {/* Logo at bottom */}
        {show_logo && logo_position === 'bottom' && brandProfile?.logo_url && (
          <img
            src={brandProfile.logo_url}
            alt="Brand logo"
            style={{
              position: 'absolute',
              bottom: 48,
              maxHeight: 60,
              maxWidth: 160,
              objectFit: 'contain',
              ...getAnimationStyle(animation, localFrame, taglineDelay + 10),
            }}
          />
        )}

        {/* Decorative accent element */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            width: '100%',
            height: 6,
            backgroundColor: accentColor,
            transform: `scaleX(${interpolate(localFrame, [0, 30], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
              easing: Easing.out(Easing.cubic),
            })})`,
            transformOrigin: 'left center',
          }}
        />
      </div>
    </Sequence>
  );
};
