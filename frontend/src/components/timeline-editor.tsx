'use client';

import { useCallback, useState, useMemo, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Layers,
  Plus,
  Minus,
  Video,
  Type,
  Wand2,
  Clock,
  Check,
  X,
  RefreshCw,
} from 'lucide-react';
import type {
  RemotionPayload,
  TimelineSegment,
  TextSlideContent,
} from '@/types/render';

// Segment type configuration
const SEGMENT_TYPE_CONFIG: Record<string, { icon: React.ReactNode; color: string; bgColor: string }> = {
  video_clip: {
    icon: <Video className="h-3 w-3" />,
    color: 'text-green-400',
    bgColor: 'bg-green-900/50',
  },
  text_slide: {
    icon: <Type className="h-3 w-3" />,
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/50',
  },
  generated_broll: {
    icon: <Wand2 className="h-3 w-3" />,
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/50',
  },
};

// Beat type colors
const BEAT_TYPE_COLORS: Record<string, string> = {
  hook: '#FF5733',
  problem: '#E74C3C',
  solution: '#27AE60',
  demo: '#3498DB',
  cta: '#9B59B6',
  testimonial: '#F39C12',
  feature: '#1ABC9C',
  default: '#7F8C8D',
};

interface TimelineEditorProps {
  payload: RemotionPayload;
  selectedSegmentId: string | null;
  currentFrame: number;
  onSegmentClick: (segment: TimelineSegment) => void;
  onSegmentUpdate: (segmentId: string, updates: Partial<TimelineSegment>) => void;
  onSeek: (frame: number) => void;
  onOpenClipSwap: (segment: TimelineSegment) => void;
  className?: string;
}

/**
 * TimelineEditor component for visualizing and editing video timeline segments.
 * Features:
 * - Visual timeline with segment blocks
 * - Click to select segments
 * - Double-click to open clip swap modal
 * - Inline text editing for text slides
 * - Drag to adjust timing (within constraints)
 * - Playhead indicator
 */
export function TimelineEditor({
  payload,
  selectedSegmentId,
  currentFrame,
  onSegmentClick,
  onSegmentUpdate,
  onSeek,
  onOpenClipSwap,
  className = '',
}: TimelineEditorProps) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [editingTextId, setEditingTextId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState<string>('');
  const timelineRef = useRef<HTMLDivElement>(null);

  // Calculate timeline dimensions
  const fps = payload.fps;
  const totalFrames = payload.duration_in_frames;
  const totalDuration = totalFrames / fps;
  const pixelsPerSecond = 100 * zoomLevel;
  const timelineWidth = totalDuration * pixelsPerSecond;

  // Calculate playhead position
  const playheadPosition = (currentFrame / fps) * pixelsPerSecond;

  // Scroll to keep playhead visible
  useEffect(() => {
    if (timelineRef.current) {
      const container = timelineRef.current;
      const containerWidth = container.clientWidth;
      const scrollLeft = container.scrollLeft;

      // If playhead is outside visible area, scroll to center it
      if (playheadPosition < scrollLeft || playheadPosition > scrollLeft + containerWidth - 50) {
        container.scrollTo({
          left: Math.max(0, playheadPosition - containerWidth / 2),
          behavior: 'smooth',
        });
      }
    }
  }, [playheadPosition]);

  // Handle segment click
  const handleSegmentClick = useCallback(
    (e: React.MouseEvent, segment: TimelineSegment) => {
      e.stopPropagation();
      onSegmentClick(segment);
    },
    [onSegmentClick]
  );

  // Handle double-click to open clip swap
  const handleSegmentDoubleClick = useCallback(
    (e: React.MouseEvent, segment: TimelineSegment) => {
      e.stopPropagation();
      if (segment.type === 'video_clip' || segment.type === 'generated_broll') {
        onOpenClipSwap(segment);
      } else if (segment.type === 'text_slide' && segment.text_content) {
        setEditingTextId(segment.id);
        setEditingText(segment.text_content.headline);
      }
    },
    [onOpenClipSwap]
  );

  // Handle timeline click to seek
  const handleTimelineClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const clickX = e.clientX - rect.left + (timelineRef.current?.scrollLeft || 0);
      const clickTime = clickX / pixelsPerSecond;
      const targetFrame = Math.round(clickTime * fps);
      onSeek(Math.max(0, Math.min(totalFrames, targetFrame)));
    },
    [pixelsPerSecond, fps, totalFrames, onSeek]
  );

  // Handle text editing
  const handleSaveText = useCallback(
    (segmentId: string) => {
      const segment = payload.timeline.find((s) => s.id === segmentId);
      if (segment?.text_content && editingText.trim()) {
        const updatedContent: TextSlideContent = {
          ...segment.text_content,
          headline: editingText.trim(),
        };
        onSegmentUpdate(segmentId, { text_content: updatedContent });
      }
      setEditingTextId(null);
      setEditingText('');
    },
    [editingText, onSegmentUpdate, payload.timeline]
  );

  const handleCancelTextEdit = useCallback(() => {
    setEditingTextId(null);
    setEditingText('');
  }, []);

  // Handle zoom
  const handleZoomIn = useCallback(() => {
    setZoomLevel((prev) => Math.min(prev + 0.5, 3));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoomLevel((prev) => Math.max(prev - 0.5, 0.5));
  }, []);

  // Generate time markers
  const timeMarkers = useMemo(() => {
    const markers: number[] = [];
    const interval = zoomLevel >= 2 ? 0.5 : zoomLevel >= 1 ? 1 : 2;
    for (let t = 0; t <= totalDuration; t += interval) {
      markers.push(t);
    }
    return markers;
  }, [totalDuration, zoomLevel]);

  // Format time display
  const formatTime = useCallback((seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.round((seconds % 1) * 10);
    if (zoomLevel >= 2) {
      return `${mins}:${secs.toString().padStart(2, '0')}.${ms}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }, [zoomLevel]);

  // Get segment color based on beat type
  const getSegmentColor = useCallback((segment: TimelineSegment) => {
    if (segment.type === 'text_slide' && segment.text_content?.background_color) {
      return segment.text_content.background_color;
    }
    const beatType = segment.beat_type?.toLowerCase() || 'default';
    return BEAT_TYPE_COLORS[beatType] || BEAT_TYPE_COLORS.default;
  }, []);

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="h-4 w-4" />
            Timeline Editor
          </CardTitle>
          <div className="flex items-center gap-2">
            {/* Current time display */}
            <Badge variant="outline" className="font-mono">
              <Clock className="h-3 w-3 mr-1" />
              {formatTime(currentFrame / fps)}
            </Badge>

            {/* Zoom controls */}
            <div className="flex items-center gap-1 border rounded-md px-1">
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleZoomOut}>
                <Minus className="h-3 w-3" />
              </Button>
              <span className="text-xs w-10 text-center">{Math.round(zoomLevel * 100)}%</span>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleZoomIn}>
                <Plus className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pb-4">
        {payload.timeline.length > 0 ? (
          <div className="space-y-2">
            {/* Timeline ruler */}
            <div
              ref={timelineRef}
              className="relative overflow-x-auto"
              style={{ height: 'auto' }}
            >
              {/* Time markers */}
              <div
                className="relative h-6 border-b border-muted"
                style={{ width: `${timelineWidth}px`, minWidth: '100%' }}
              >
                {timeMarkers.map((time) => (
                  <div
                    key={time}
                    className="absolute top-0 flex flex-col items-center"
                    style={{ left: `${time * pixelsPerSecond}px` }}
                  >
                    <div className="h-2 w-px bg-muted-foreground/50" />
                    <span className="text-[10px] text-muted-foreground">
                      {formatTime(time)}
                    </span>
                  </div>
                ))}
              </div>

              {/* Timeline track */}
              <div
                className="relative h-20 mt-1 cursor-crosshair"
                style={{ width: `${timelineWidth}px`, minWidth: '100%' }}
                onClick={handleTimelineClick}
              >
                {/* Segment blocks */}
                {payload.timeline.map((segment) => {
                  const startTime = segment.start_frame / fps;
                  const duration = segment.duration_frames / fps;
                  const left = startTime * pixelsPerSecond;
                  const width = Math.max(duration * pixelsPerSecond - 2, 30);
                  const isSelected = selectedSegmentId === segment.id;
                  const config = SEGMENT_TYPE_CONFIG[segment.type] || SEGMENT_TYPE_CONFIG.video_clip;
                  const bgColor = getSegmentColor(segment);

                  return (
                    <div
                      key={segment.id}
                      className={`absolute top-1 h-[72px] rounded cursor-pointer transition-all ${
                        isSelected ? 'ring-2 ring-primary ring-offset-1 z-10' : 'hover:brightness-110'
                      }`}
                      style={{
                        left: `${left}px`,
                        width: `${width}px`,
                        backgroundColor: bgColor,
                      }}
                      onClick={(e) => handleSegmentClick(e, segment)}
                      onDoubleClick={(e) => handleSegmentDoubleClick(e, segment)}
                    >
                      <div className="p-1.5 h-full flex flex-col overflow-hidden">
                        {/* Segment header */}
                        <div className="flex items-center gap-1 mb-1">
                          <span className={config.color}>{config.icon}</span>
                          <span className="text-[10px] text-white/80 truncate flex-1">
                            {segment.beat_type || segment.type.replace('_', ' ')}
                          </span>
                          {segment.similarity_score !== undefined && segment.similarity_score !== null && (
                            <Badge variant="secondary" className="h-4 text-[8px] px-1">
                              {Math.round(segment.similarity_score * 100)}%
                            </Badge>
                          )}
                        </div>

                        {/* Segment content preview */}
                        <div className="flex-1 overflow-hidden">
                          {editingTextId === segment.id ? (
                            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                              <Input
                                value={editingText}
                                onChange={(e) => setEditingText(e.target.value)}
                                className="h-6 text-xs bg-black/30 border-white/30"
                                autoFocus
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') handleSaveText(segment.id);
                                  if (e.key === 'Escape') handleCancelTextEdit();
                                }}
                              />
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6"
                                onClick={() => handleSaveText(segment.id)}
                              >
                                <Check className="h-3 w-3 text-green-400" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6"
                                onClick={handleCancelTextEdit}
                              >
                                <X className="h-3 w-3 text-red-400" />
                              </Button>
                            </div>
                          ) : (
                            <>
                              {segment.type === 'text_slide' && segment.text_content ? (
                                <p className="text-xs text-white/90 truncate">
                                  {segment.text_content.headline}
                                </p>
                              ) : segment.overlay?.text ? (
                                <p className="text-xs text-white/80 truncate italic">
                                  &ldquo;{segment.overlay.text}&rdquo;
                                </p>
                              ) : segment.generated_source?.generation_prompt ? (
                                <p className="text-xs text-white/70 truncate">
                                  {segment.generated_source.generation_prompt}
                                </p>
                              ) : null}
                            </>
                          )}
                        </div>

                        {/* Duration */}
                        <div className="flex items-center justify-between mt-auto">
                          <span className="text-[10px] text-white/60">
                            {duration.toFixed(1)}s
                          </span>
                          {(segment.type === 'video_clip' || segment.type === 'generated_broll') && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-5 w-5 text-white/60 hover:text-white"
                              onClick={(e) => {
                                e.stopPropagation();
                                onOpenClipSwap(segment);
                              }}
                            >
                              <RefreshCw className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* Playhead */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20 pointer-events-none"
                  style={{ left: `${playheadPosition}px` }}
                >
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-red-500" />
                </div>
              </div>
            </div>

            {/* Segment legend */}
            <div className="flex items-center gap-4 pt-2 border-t">
              <span className="text-xs text-muted-foreground">Segment types:</span>
              {Object.entries(SEGMENT_TYPE_CONFIG).map(([type, config]) => (
                <div key={type} className="flex items-center gap-1">
                  <div className={`p-1 rounded ${config.bgColor}`}>
                    {config.icon}
                  </div>
                  <span className="text-xs text-muted-foreground capitalize">
                    {type.replace('_', ' ')}
                  </span>
                </div>
              ))}
            </div>

            {/* Instructions */}
            <div className="text-xs text-muted-foreground text-center">
              Click segment to select &bull; Double-click to edit/swap &bull; Click timeline to seek
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Layers className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No segments in timeline</p>
            <p className="text-xs mt-1">Generate an ad to see the timeline</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default TimelineEditor;
