'use client';

import { useCallback, useState, useMemo } from 'react';
import { Player, PlayerRef } from '@remotion/player';
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  Video,
  interpolate,
} from 'remotion';
import { useRef, forwardRef, useImperativeHandle } from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Maximize,
  Minimize,
} from 'lucide-react';
import type {
  RemotionPayload,
  TimelineSegment,
  TextOverlay,
  CompositionType,
} from '@/types/render';

// Composition dimensions
const DIMENSIONS: Record<CompositionType, { width: number; height: number }> = {
  vertical_ad_v1: { width: 1080, height: 1920 },
  horizontal_ad_v1: { width: 1920, height: 1080 },
  square_ad_v1: { width: 1080, height: 1080 },
};

// Text overlay component
interface TextOverlayProps {
  overlay: TextOverlay;
  frame: number;
}

const TextOverlayRenderer: React.FC<TextOverlayProps> = ({ overlay, frame }) => {
  const { text, position = 'center', font_size = 48, font_weight = 'bold', color = '#FFFFFF', background, animation = 'none' } = overlay;

  // Calculate animation progress
  const animationDuration = 15; // frames
  let opacity = 1;
  let scale = 1;
  let translateY = 0;

  switch (animation) {
    case 'fade_in':
      opacity = interpolate(frame, [0, animationDuration], [0, 1], { extrapolateRight: 'clamp' });
      break;
    case 'pop_in':
      const progress = interpolate(frame, [0, animationDuration], [0, 1], { extrapolateRight: 'clamp' });
      scale = interpolate(progress, [0, 0.5, 1], [0.5, 1.1, 1]);
      opacity = interpolate(frame, [0, animationDuration / 2], [0, 1], { extrapolateRight: 'clamp' });
      break;
    case 'slide_up':
      translateY = interpolate(frame, [0, animationDuration], [50, 0], { extrapolateRight: 'clamp' });
      opacity = interpolate(frame, [0, animationDuration], [0, 1], { extrapolateRight: 'clamp' });
      break;
  }

  // Position styles
  const getPositionStyles = (): React.CSSProperties => {
    switch (position) {
      case 'top':
        return { top: '10%', left: '50%', transform: `translateX(-50%) scale(${scale}) translateY(${translateY}px)` };
      case 'bottom':
        return { bottom: '10%', left: '50%', transform: `translateX(-50%) scale(${scale}) translateY(${translateY}px)` };
      case 'lower-third':
        return { bottom: '20%', left: '50%', transform: `translateX(-50%) scale(${scale}) translateY(${translateY}px)` };
      case 'center':
      default:
        return { top: '50%', left: '50%', transform: `translate(-50%, -50%) scale(${scale}) translateY(${translateY}px)` };
    }
  };

  return (
    <div
      style={{
        position: 'absolute',
        ...getPositionStyles(),
        opacity,
        fontSize: font_size,
        fontWeight: font_weight,
        color: color,
        backgroundColor: background || 'transparent',
        padding: background ? '8px 16px' : 0,
        borderRadius: background ? 8 : 0,
        whiteSpace: 'nowrap',
        textAlign: 'center',
        fontFamily: 'Inter, sans-serif',
        textShadow: !background ? '2px 2px 4px rgba(0,0,0,0.5)' : 'none',
      }}
    >
      {text}
    </div>
  );
};

// Segment renderer component
interface SegmentRendererProps {
  segment: TimelineSegment;
}

const SegmentRenderer: React.FC<SegmentRendererProps> = ({ segment }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = frame - segment.start_frame;

  // Render based on segment type
  const renderContent = () => {
    switch (segment.type) {
      case 'video_clip':
        if (!segment.source?.url) {
          // Show placeholder for video clips without a valid URL
          return (
            <div
              style={{
                width: '100%',
                height: '100%',
                backgroundColor: '#1a1a1a',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '10%',
              }}
            >
              <div style={{ color: '#888', fontSize: 24, textAlign: 'center' }}>
                Video Pending
              </div>
              <div style={{ color: '#666', fontSize: 16, marginTop: 10, textAlign: 'center' }}>
                {segment.search_query || 'No video source available'}
              </div>
            </div>
          );
        }
        return (
          <Video
            src={segment.source.url}
            startFrom={Math.round(segment.source.start_time * fps)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        );

      case 'text_slide':
        if (!segment.text_content) return null;
        return (
          <div
            style={{
              width: '100%',
              height: '100%',
              backgroundColor: segment.text_content.background_color || '#1a1a1a',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '10%',
            }}
          >
            <h1
              style={{
                color: segment.text_content.text_color || '#FFFFFF',
                fontSize: 72,
                fontWeight: 'bold',
                textAlign: 'center',
                marginBottom: 20,
              }}
            >
              {segment.text_content.headline}
            </h1>
            {segment.text_content.subheadline && (
              <p
                style={{
                  color: segment.text_content.text_color || '#FFFFFF',
                  fontSize: 36,
                  textAlign: 'center',
                  opacity: 0.9,
                }}
              >
                {segment.text_content.subheadline}
              </p>
            )}
          </div>
        );

      case 'generated_broll':
        if (!segment.generated_source?.url) {
          // Show placeholder for pending B-Roll generation
          return (
            <div
              style={{
                width: '100%',
                height: '100%',
                backgroundColor: '#2a2a2a',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '10%',
              }}
            >
              <div style={{ color: '#888', fontSize: 24, textAlign: 'center' }}>
                B-Roll Pending
              </div>
              <div style={{ color: '#666', fontSize: 16, marginTop: 10, textAlign: 'center' }}>
                {segment.generated_source?.generation_prompt || 'No prompt available'}
              </div>
            </div>
          );
        }
        return (
          <Video
            src={segment.generated_source.url}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        );

      default:
        return null;
    }
  };

  return (
    <Sequence from={segment.start_frame} durationInFrames={segment.duration_frames}>
      <AbsoluteFill>
        {renderContent()}
        {segment.overlay && (
          <TextOverlayRenderer
            overlay={segment.overlay}
            frame={localFrame}
          />
        )}
      </AbsoluteFill>
    </Sequence>
  );
};

// Main composition component
interface AdCompositionProps {
  payload: RemotionPayload;
}

const AdComposition: React.FC<AdCompositionProps> = ({ payload }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#000000' }}>
      {payload.timeline.map((segment) => (
        <SegmentRenderer key={segment.id} segment={segment} />
      ))}
    </AbsoluteFill>
  );
};

// Player component props
export interface RemotionPlayerProps {
  payload: RemotionPayload;
  onSegmentClick?: (segment: TimelineSegment) => void;
  className?: string;
  autoPlay?: boolean;
  loop?: boolean;
  showControls?: boolean;
}

export interface RemotionPlayerHandle {
  play: () => void;
  pause: () => void;
  seekTo: (frame: number) => void;
  getCurrentFrame: () => number;
  isPlaying: () => boolean;
}

/**
 * RemotionPlayer component that embeds a Remotion Player for real-time preview.
 * Renders the timeline segments directly using @remotion/player.
 */
export const RemotionPlayer = forwardRef<RemotionPlayerHandle, RemotionPlayerProps>(
  ({ payload, onSegmentClick, className = '', autoPlay = false, loop = true, showControls = true }, ref) => {
    const playerRef = useRef<PlayerRef>(null);
    const [isPlaying, setIsPlaying] = useState(autoPlay);
    const [isMuted, setIsMuted] = useState(false);
    const [currentFrame, setCurrentFrame] = useState(0);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const dimensions = DIMENSIONS[payload.composition_id] || DIMENSIONS.vertical_ad_v1;

    // Expose player controls via ref
    useImperativeHandle(ref, () => ({
      play: () => {
        playerRef.current?.play();
        setIsPlaying(true);
      },
      pause: () => {
        playerRef.current?.pause();
        setIsPlaying(false);
      },
      seekTo: (frame: number) => {
        playerRef.current?.seekTo(frame);
        setCurrentFrame(frame);
      },
      getCurrentFrame: () => currentFrame,
      isPlaying: () => isPlaying,
    }));

    const handlePlayPause = useCallback(() => {
      if (isPlaying) {
        playerRef.current?.pause();
        setIsPlaying(false);
      } else {
        playerRef.current?.play();
        setIsPlaying(true);
      }
    }, [isPlaying]);

    const handleMuteToggle = useCallback(() => {
      setIsMuted(!isMuted);
    }, [isMuted]);

    const handleSeek = useCallback((value: number[]) => {
      const frame = value[0];
      playerRef.current?.seekTo(frame);
      setCurrentFrame(frame);
    }, []);

    const handleSkipBack = useCallback(() => {
      const newFrame = Math.max(0, currentFrame - 30);
      playerRef.current?.seekTo(newFrame);
      setCurrentFrame(newFrame);
    }, [currentFrame]);

    const handleSkipForward = useCallback(() => {
      const newFrame = Math.min(payload.duration_in_frames, currentFrame + 30);
      playerRef.current?.seekTo(newFrame);
      setCurrentFrame(newFrame);
    }, [currentFrame, payload.duration_in_frames]);

    const handleFullscreenToggle = useCallback(() => {
      if (!containerRef.current) return;

      if (!document.fullscreenElement) {
        containerRef.current.requestFullscreen();
        setIsFullscreen(true);
      } else {
        document.exitFullscreen();
        setIsFullscreen(false);
      }
    }, []);

    // Format time as MM:SS
    const formatTime = (frame: number) => {
      const seconds = Math.floor(frame / payload.fps);
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    // Find current segment for display
    const currentSegment = useMemo(() => {
      return payload.timeline.find(
        (seg) => currentFrame >= seg.start_frame && currentFrame < seg.start_frame + seg.duration_frames
      );
    }, [currentFrame, payload.timeline]);

    // Calculate aspect ratio for responsive sizing
    const aspectRatio = dimensions.width / dimensions.height;

    return (
      <div ref={containerRef} className={`flex flex-col ${className}`}>
        {/* Player container */}
        <div
          className="relative bg-black rounded-lg overflow-hidden"
          style={{
            aspectRatio: `${aspectRatio}`,
            maxHeight: isFullscreen ? '100vh' : '70vh',
          }}
        >
          <Player
            ref={playerRef}
            component={AdComposition}
            inputProps={{ payload }}
            durationInFrames={payload.duration_in_frames}
            fps={payload.fps}
            compositionWidth={dimensions.width}
            compositionHeight={dimensions.height}
            style={{
              width: '100%',
              height: '100%',
            }}
            autoPlay={autoPlay}
            loop={loop}
            controls={false}
            spaceKeyToPlayOrPause
            moveToBeginningWhenEnded={loop}
            clickToPlay={!showControls}
          />

          {/* Current segment indicator */}
          {currentSegment && (
            <div className="absolute top-2 left-2 z-10">
              <Badge
                variant="secondary"
                className="bg-black/70 text-white text-xs cursor-pointer hover:bg-black/90"
                onClick={() => onSegmentClick?.(currentSegment)}
              >
                {currentSegment.beat_type || currentSegment.type}
              </Badge>
            </div>
          )}
        </div>

        {/* Custom controls */}
        {showControls && (
          <div className="mt-3 space-y-2">
            {/* Seek slider */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-12 text-right">
                {formatTime(currentFrame)}
              </span>
              <Slider
                value={[currentFrame]}
                min={0}
                max={payload.duration_in_frames}
                step={1}
                onValueChange={handleSeek}
                className="flex-1"
              />
              <span className="text-xs text-muted-foreground w-12">
                {formatTime(payload.duration_in_frames)}
              </span>
            </div>

            {/* Control buttons */}
            <div className="flex items-center justify-center gap-2">
              <Button variant="ghost" size="icon" onClick={handleSkipBack}>
                <SkipBack className="h-4 w-4" />
              </Button>
              <Button variant="default" size="icon" onClick={handlePlayPause}>
                {isPlaying ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
              <Button variant="ghost" size="icon" onClick={handleSkipForward}>
                <SkipForward className="h-4 w-4" />
              </Button>
              <div className="flex-1" />
              <Button variant="ghost" size="icon" onClick={handleMuteToggle}>
                {isMuted ? (
                  <VolumeX className="h-4 w-4" />
                ) : (
                  <Volume2 className="h-4 w-4" />
                )}
              </Button>
              <Button variant="ghost" size="icon" onClick={handleFullscreenToggle}>
                {isFullscreen ? (
                  <Minimize className="h-4 w-4" />
                ) : (
                  <Maximize className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  }
);

RemotionPlayer.displayName = 'RemotionPlayer';

export default RemotionPlayer;
