import React from 'react';
import {
  OffthreadVideo,
  useVideoConfig,
  Sequence,
  useCurrentFrame,
} from 'remotion';
import type { VideoClipSource, TextOverlay, Transition, BrandProfile } from '../types';
import { TextOverlayComponent } from './TextOverlay';
import { applyTransitionIn, applyTransitionOut } from '../utils/transitions';

interface Props {
  source: VideoClipSource;
  startFrame: number;
  durationFrames: number;
  overlay?: TextOverlay | null;
  transitionIn?: Transition | null;
  transitionOut?: Transition | null;
  brandProfile?: BrandProfile | null;
}

interface VideoErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary component for catching video loading errors.
 */
class VideoErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback: React.ReactNode },
  VideoErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; fallback: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): VideoErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('VideoClipSegment error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

/**
 * Checks if a URL is valid for video playback.
 */
function isValidVideoUrl(url: string | undefined | null): boolean {
  if (!url || typeof url !== 'string') {
    return false;
  }
  const trimmed = url.trim();
  if (trimmed === '' || trimmed === 'null' || trimmed === 'undefined') {
    return false;
  }
  // Check for valid URL patterns (http, https, blob, data, or relative paths)
  return (
    trimmed.startsWith('http://') ||
    trimmed.startsWith('https://') ||
    trimmed.startsWith('blob:') ||
    trimmed.startsWith('data:') ||
    trimmed.startsWith('/') ||
    trimmed.startsWith('.')
  );
}

/**
 * Placeholder component shown when video URL is missing or invalid.
 */
const VideoPlaceholder: React.FC<{
  backgroundColor: string;
  message: string;
  subMessage?: string;
}> = ({ backgroundColor, message, subMessage }) => {
  return (
    <div
      style={{
        position: 'absolute',
        width: '100%',
        height: '100%',
        backgroundColor,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 48,
      }}
    >
      {/* Video icon placeholder */}
      <div
        style={{
          width: 120,
          height: 120,
          borderRadius: 60,
          backgroundColor: 'rgba(255,255,255,0.1)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <svg
          width="60"
          height="60"
          viewBox="0 0 24 24"
          fill="none"
          stroke="rgba(255,255,255,0.5)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {/* Video camera icon */}
          <polygon points="23 7 16 12 23 17 23 7" />
          <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
        </svg>
      </div>

      {/* Main message */}
      <span
        style={{
          fontSize: 24,
          color: 'rgba(255,255,255,0.7)',
          fontFamily: 'Inter, sans-serif',
          marginBottom: 12,
          textAlign: 'center',
        }}
      >
        {message}
      </span>

      {/* Sub message */}
      {subMessage && (
        <span
          style={{
            fontSize: 16,
            color: 'rgba(255,255,255,0.4)',
            fontFamily: 'Inter, sans-serif',
            textAlign: 'center',
            maxWidth: '80%',
            lineHeight: 1.4,
          }}
        >
          {subMessage}
        </span>
      )}
    </div>
  );
};

export const VideoClipSegment: React.FC<Props> = ({
  source,
  startFrame,
  durationFrames,
  overlay,
  transitionIn,
  transitionOut,
  brandProfile,
}) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();

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
  const combinedTranslateX =
    (transInStyle.translateX ?? 0) + (transOutStyle.translateX ?? 0);
  const combinedTranslateY =
    (transInStyle.translateY ?? 0) + (transOutStyle.translateY ?? 0);

  const backgroundColor = brandProfile?.primary_color || '#1a1a2e';

  // Check for valid URL
  const hasValidUrl = isValidVideoUrl(source?.url);

  // Placeholder fallback for error boundary
  const placeholderFallback = (
    <div
      style={{
        position: 'absolute',
        width: '100%',
        height: '100%',
        opacity: combinedOpacity,
        transform: `translate(${combinedTranslateX}px, ${combinedTranslateY}px) scale(${combinedScale})`,
      }}
    >
      <VideoPlaceholder
        backgroundColor={backgroundColor}
        message="Video Load Error"
        subMessage="Failed to load video source"
      />
      {overlay && (
        <TextOverlayComponent {...overlay} segmentStartFrame={startFrame} />
      )}
    </div>
  );

  // If URL is missing or invalid, show placeholder
  if (!hasValidUrl) {
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
          <VideoPlaceholder
            backgroundColor={backgroundColor}
            message="Missing Video"
            subMessage={
              source?.url
                ? `Invalid URL: ${source.url.substring(0, 50)}${source.url.length > 50 ? '...' : ''}`
                : 'No video source provided'
            }
          />
          {overlay && (
            <TextOverlayComponent {...overlay} segmentStartFrame={startFrame} />
          )}
        </div>
      </Sequence>
    );
  }

  return (
    <Sequence from={startFrame} durationInFrames={durationFrames}>
      <VideoErrorBoundary fallback={placeholderFallback}>
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
            <TextOverlayComponent {...overlay} segmentStartFrame={startFrame} />
          )}
        </div>
      </VideoErrorBoundary>
    </Sequence>
  );
};
