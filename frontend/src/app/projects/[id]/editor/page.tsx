'use client';

import Link from 'next/link';
import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useProject, useSearchSegments } from '@/hooks/useProjects';
import {
  useProjectRenders,
  useCreateRender,
  useRenderStatus,
  useCancelRender,
} from '@/hooks/useRender';
import { RemotionPlayer, RemotionPlayerHandle } from '@/components/remotion-player';
import { TimelineEditor } from '@/components/timeline-editor';
import { ClipSwapModal } from '@/components/clip-swap-modal';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Film,
  Download,
  Clock,
  CheckCircle,
  XCircle,
  Play,
  Settings,
  Wand2,
  FileVideo,
  Layers,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type {
  RemotionPayload,
  TimelineSegment,
  RenderStatus,
  CompositionType,
  VideoClipSource,
} from '@/types/render';
import type { UserVideoSegmentWithSimilarity } from '@/types/project';

// Status configuration for render jobs
const renderStatusConfig: Record<
  RenderStatus,
  { label: string; icon: React.ReactNode; color: string }
> = {
  pending: { label: 'Pending', icon: <Clock className="h-4 w-4" />, color: 'text-yellow-500' },
  rendering: { label: 'Rendering', icon: <Loader2 className="h-4 w-4 animate-spin" />, color: 'text-blue-500' },
  completed: { label: 'Completed', icon: <CheckCircle className="h-4 w-4" />, color: 'text-green-500' },
  failed: { label: 'Failed', icon: <XCircle className="h-4 w-4" />, color: 'text-red-500' },
};

// Sample payload for preview (when no payload exists yet)
const createSamplePayload = (projectId: string): RemotionPayload => ({
  composition_id: 'vertical_ad_v1',
  width: 1080,
  height: 1920,
  fps: 30,
  duration_in_frames: 450,
  project_id: projectId,
  timeline: [
    {
      id: 'sample-hook',
      type: 'video_clip',
      start_frame: 0,
      duration_frames: 90,
      beat_type: 'hook',
      search_query: 'energetic action, product reveal',
      similarity_score: 0.85,
      source: {
        url: '',
        start_time: 0,
        end_time: 3,
      },
      overlay: {
        text: 'Stop Wasting Money!',
        position: 'center',
        font_size: 48,
        color: '#FFFFFF',
        animation: 'pop_in',
      },
    },
    {
      id: 'sample-problem',
      type: 'video_clip',
      start_frame: 90,
      duration_frames: 120,
      beat_type: 'problem',
      search_query: 'frustrated expression, pain point',
      similarity_score: 0.72,
      source: {
        url: '',
        start_time: 0,
        end_time: 4,
      },
      overlay: {
        text: 'Is your sink leaking?',
        position: 'bottom',
        font_size: 36,
        color: '#FFFFFF',
      },
    },
    {
      id: 'sample-broll',
      type: 'generated_broll',
      start_frame: 210,
      duration_frames: 90,
      beat_type: 'solution',
      generated_source: {
        url: null,
        generation_prompt: 'Water dripping from faucet, slow motion, cinematic lighting',
        regenerate_available: true,
      },
    },
    {
      id: 'sample-cta',
      type: 'text_slide',
      start_frame: 300,
      duration_frames: 150,
      beat_type: 'cta',
      text_content: {
        headline: '50% OFF Today Only!',
        subheadline: 'Use code SUMMER50',
        background_color: '#FF5733',
        text_color: '#FFFFFF',
      },
    },
  ],
});

// Alternative clip type for the modal
interface AlternativeClip {
  id: string;
  segment: UserVideoSegmentWithSimilarity;
  similarity_score: number;
}

interface PageProps {
  params: { id: string };
}

export default function EditorPage({ params }: PageProps) {
  const { id } = params;
  const { data: project, isLoading: projectLoading, error: projectError } = useProject(id);
  const { data: rendersData, isLoading: rendersLoading } = useProjectRenders(id);
  const createRenderMutation = useCreateRender();
  const cancelRenderMutation = useCancelRender();
  const searchSegmentsMutation = useSearchSegments();

  const [activeRenderId, setActiveRenderId] = useState<string | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<TimelineSegment | null>(null);
  const [compositionType, setCompositionType] = useState<CompositionType>('vertical_ad_v1');
  const [currentFrame, setCurrentFrame] = useState(0);
  const [localPayload, setLocalPayload] = useState<RemotionPayload | null>(null);

  // Clip swap modal state
  const [clipSwapOpen, setClipSwapOpen] = useState(false);
  const [swapSegment, setSwapSegment] = useState<TimelineSegment | null>(null);
  const [alternativeClips, setAlternativeClips] = useState<AlternativeClip[]>([]);
  const [isLoadingAlternatives, setIsLoadingAlternatives] = useState(false);

  const playerRef = useRef<RemotionPlayerHandle>(null);

  // Poll for active render status
  const { data: activeRenderStatus } = useRenderStatus(activeRenderId, {
    poll: activeRenderId !== null,
  });

  // Initialize local payload
  useEffect(() => {
    if (!localPayload && project) {
      setLocalPayload(createSamplePayload(id));
    }
  }, [project, id, localPayload]);

  // Get current payload (from local state or sample)
  const currentPayload: RemotionPayload | null = useMemo(() => {
    if (activeRenderStatus?.video_url) {
      return null; // Will show video player instead
    }
    return localPayload;
  }, [localPayload, activeRenderStatus?.video_url]);

  // Handle render completion
  useEffect(() => {
    if (activeRenderStatus?.status === 'completed') {
      toast.success('Video rendered successfully!');
    } else if (activeRenderStatus?.status === 'failed') {
      toast.error('Rendering failed. Please try again.');
    }
  }, [activeRenderStatus?.status]);

  // Handle segment click from player or timeline
  const handleSegmentClick = useCallback((segment: TimelineSegment) => {
    setSelectedSegment(segment);
  }, []);

  // Handle opening clip swap modal
  const handleOpenClipSwap = useCallback(async (segment: TimelineSegment) => {
    setSwapSegment(segment);
    setClipSwapOpen(true);
    setAlternativeClips([]);

    // Search for alternatives if segment has a search query
    if (segment.search_query) {
      setIsLoadingAlternatives(true);
      try {
        const results = await searchSegmentsMutation.mutateAsync({
          projectId: id,
          request: {
            query: segment.search_query,
            limit: 10,
            min_similarity: 0.3,
          },
        });

        const clips: AlternativeClip[] = results.results.map((seg) => ({
          id: seg.id,
          segment: seg,
          similarity_score: seg.similarity_score,
        }));
        setAlternativeClips(clips);
      } catch (error) {
        console.error('Failed to search for alternatives:', error);
        toast.error('Failed to load alternative clips');
      } finally {
        setIsLoadingAlternatives(false);
      }
    }
  }, [id, searchSegmentsMutation]);

  // Handle segment update (for inline editing)
  const handleSegmentUpdate = useCallback(
    (segmentId: string, updates: Partial<TimelineSegment>) => {
      if (!localPayload) return;

      const updatedTimeline = localPayload.timeline.map((seg) =>
        seg.id === segmentId ? { ...seg, ...updates } : seg
      );

      const updatedPayload = {
        ...localPayload,
        timeline: updatedTimeline,
      };

      setLocalPayload(updatedPayload);

      // Update selected segment if it's the one being edited
      if (selectedSegment?.id === segmentId) {
        setSelectedSegment({ ...selectedSegment, ...updates });
      }

      toast.success('Segment updated');
    },
    [localPayload, selectedSegment]
  );

  // Handle clip swap
  const handleSwapClip = useCallback(
    (segmentId: string, newSource: VideoClipSource) => {
      if (!localPayload) return;

      const updatedTimeline = localPayload.timeline.map((seg) =>
        seg.id === segmentId
          ? {
              ...seg,
              type: 'video_clip' as const,
              source: newSource,
              generated_source: undefined,
            }
          : seg
      );

      setLocalPayload({
        ...localPayload,
        timeline: updatedTimeline,
      });

      toast.success('Clip swapped successfully');
    },
    [localPayload]
  );

  // Handle B-Roll regeneration request
  const handleRegenerateBRoll = useCallback(
    (segmentId: string, prompt: string) => {
      // In a real implementation, this would call an API to regenerate B-Roll
      toast.info('B-Roll regeneration requested. This feature requires Veo 2 integration.');

      // Update the prompt in the local state
      if (!localPayload) return;

      const updatedTimeline = localPayload.timeline.map((seg) =>
        seg.id === segmentId && seg.type === 'generated_broll'
          ? {
              ...seg,
              generated_source: {
                ...seg.generated_source,
                generation_prompt: prompt,
              },
            }
          : seg
      );

      setLocalPayload({
        ...localPayload,
        timeline: updatedTimeline,
      });
    },
    [localPayload]
  );

  // Handle overlay update
  const handleUpdateOverlay = useCallback(
    (segmentId: string, text: string) => {
      if (!localPayload) return;

      const updatedTimeline = localPayload.timeline.map((seg) =>
        seg.id === segmentId
          ? {
              ...seg,
              overlay: seg.overlay
                ? { ...seg.overlay, text }
                : { text, position: 'center' as const },
            }
          : seg
      );

      setLocalPayload({
        ...localPayload,
        timeline: updatedTimeline,
      });

      toast.success('Overlay text updated');
    },
    [localPayload]
  );

  // Handle duration update
  const handleUpdateDuration = useCallback(
    (segmentId: string, durationFrames: number) => {
      if (!localPayload) return;

      // Find the segment and calculate frame offset
      const segmentIndex = localPayload.timeline.findIndex((s) => s.id === segmentId);
      if (segmentIndex === -1) return;

      const segment = localPayload.timeline[segmentIndex];
      const frameDiff = durationFrames - segment.duration_frames;

      // Update this segment and shift all subsequent segments
      const updatedTimeline = localPayload.timeline.map((seg, idx) => {
        if (seg.id === segmentId) {
          return { ...seg, duration_frames: durationFrames };
        }
        if (idx > segmentIndex) {
          return { ...seg, start_frame: seg.start_frame + frameDiff };
        }
        return seg;
      });

      // Update total duration
      const newTotalFrames = localPayload.duration_in_frames + frameDiff;

      setLocalPayload({
        ...localPayload,
        timeline: updatedTimeline,
        duration_in_frames: newTotalFrames,
      });

      toast.success('Duration updated');
    },
    [localPayload]
  );

  // Handle seek from timeline
  const handleSeek = useCallback((frame: number) => {
    setCurrentFrame(frame);
    playerRef.current?.seekTo(frame);
  }, []);

  // Handle search clips from modal
  const handleSearchClips = useCallback(async (query: string) => {
    setIsLoadingAlternatives(true);
    try {
      const results = await searchSegmentsMutation.mutateAsync({
        projectId: id,
        request: {
          query,
          limit: 10,
          min_similarity: 0.3,
        },
      });

      const clips: AlternativeClip[] = results.results.map((seg) => ({
        id: seg.id,
        segment: seg,
        similarity_score: seg.similarity_score,
      }));
      setAlternativeClips(clips);
    } catch (error) {
      console.error('Failed to search clips:', error);
      toast.error('Search failed');
    } finally {
      setIsLoadingAlternatives(false);
    }
  }, [id, searchSegmentsMutation]);

  const handleStartRender = async () => {
    if (!currentPayload) return;

    try {
      const result = await createRenderMutation.mutateAsync({
        project_id: id,
        payload: { ...currentPayload, composition_id: compositionType },
        mode: 'local',
      });
      setActiveRenderId(result.id);
      toast.info('Rendering started...');
    } catch {
      toast.error('Failed to start rendering');
    }
  };

  const handleCancelRender = async () => {
    if (!activeRenderId) return;

    try {
      await cancelRenderMutation.mutateAsync(activeRenderId);
      setActiveRenderId(null);
      toast.info('Render cancelled');
    } catch {
      toast.error('Failed to cancel render');
    }
  };

  const handleDownload = () => {
    if (activeRenderStatus?.video_url) {
      window.open(activeRenderStatus.video_url, '_blank');
    }
  };

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (projectError || !project) {
    return (
      <div className="space-y-6">
        <Link href="/projects">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Projects
          </Button>
        </Link>
        <Card>
          <CardContent className="flex flex-col items-center justify-center h-64">
            <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
            <p className="text-gray-500">Project not found</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isRendering = activeRenderStatus?.status === 'rendering';
  const isPending = activeRenderStatus?.status === 'pending';
  const isCompleted = activeRenderStatus?.status === 'completed';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Link href={`/projects/${id}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{project.name}</h1>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
              <span className="text-xl text-muted-foreground">Editor</span>
            </div>
          </div>
        </div>

        {/* Render actions */}
        <div className="flex items-center gap-2">
          {isCompleted && activeRenderStatus?.video_url && (
            <Button variant="outline" onClick={handleDownload}>
              <Download className="mr-2 h-4 w-4" />
              Download
            </Button>
          )}

          {(isRendering || isPending) && (
            <Button variant="outline" onClick={handleCancelRender} disabled={cancelRenderMutation.isPending}>
              <XCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}

          <Button
            onClick={handleStartRender}
            disabled={createRenderMutation.isPending || isRendering || isPending || !currentPayload}
          >
            {createRenderMutation.isPending || isRendering || isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {isRendering ? 'Rendering...' : 'Starting...'}
              </>
            ) : (
              <>
                <Film className="mr-2 h-4 w-4" />
                Render Video
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Player area */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Play className="h-4 w-4" />
                  Preview
                </CardTitle>
                <Select
                  value={compositionType}
                  onValueChange={(v) => setCompositionType(v as CompositionType)}
                >
                  <SelectTrigger className="w-[140px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="vertical_ad_v1">Vertical (9:16)</SelectItem>
                    <SelectItem value="horizontal_ad_v1">Horizontal (16:9)</SelectItem>
                    <SelectItem value="square_ad_v1">Square (1:1)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {/* Render status indicator */}
              {activeRenderStatus && (
                <div className="mb-4 p-3 rounded-lg bg-muted/50 flex items-center gap-3">
                  <span className={renderStatusConfig[activeRenderStatus.status].color}>
                    {renderStatusConfig[activeRenderStatus.status].icon}
                  </span>
                  <span className="text-sm font-medium">
                    {renderStatusConfig[activeRenderStatus.status].label}
                  </span>
                  {isRendering && (
                    <div className="flex-1">
                      <Progress value={activeRenderStatus.progress} className="h-2" />
                    </div>
                  )}
                  {isCompleted && activeRenderStatus.render_time_seconds && (
                    <span className="text-xs text-muted-foreground">
                      Rendered in {activeRenderStatus.render_time_seconds.toFixed(1)}s
                    </span>
                  )}
                </div>
              )}

              {/* Video player (completed) or Remotion player (preview) */}
              {isCompleted && activeRenderStatus?.video_url ? (
                <div className="relative bg-black rounded-lg overflow-hidden aspect-[9/16] max-h-[70vh]">
                  <video
                    src={activeRenderStatus.video_url}
                    controls
                    className="w-full h-full object-contain"
                  />
                </div>
              ) : currentPayload ? (
                <RemotionPlayer
                  ref={playerRef}
                  payload={{ ...currentPayload, composition_id: compositionType }}
                  onSegmentClick={handleSegmentClick}
                  showControls
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                  <FileVideo className="h-12 w-12 mb-4 opacity-50" />
                  <p>No video to preview</p>
                  <Button asChild variant="link" className="mt-2">
                    <Link href={`/projects/${id}/inspire`}>
                      <Wand2 className="mr-2 h-4 w-4" />
                      Generate an ad first
                    </Link>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right sidebar */}
        <div className="space-y-4">
          {/* Selected segment details */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Layers className="h-4 w-4" />
                Segment Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedSegment ? (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs text-muted-foreground uppercase tracking-wide">
                      Type
                    </label>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary">{selectedSegment.type.replace('_', ' ')}</Badge>
                      {selectedSegment.beat_type && (
                        <Badge variant="outline">{selectedSegment.beat_type}</Badge>
                      )}
                    </div>
                  </div>

                  <Separator />

                  <div>
                    <label className="text-xs text-muted-foreground uppercase tracking-wide">
                      Timing
                    </label>
                    <p className="text-sm mt-1">
                      Frame {selectedSegment.start_frame} -{' '}
                      {selectedSegment.start_frame + selectedSegment.duration_frames}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Duration: {(selectedSegment.duration_frames / 30).toFixed(1)}s
                    </p>
                  </div>

                  {selectedSegment.overlay && (
                    <>
                      <Separator />
                      <div>
                        <label className="text-xs text-muted-foreground uppercase tracking-wide">
                          Overlay Text
                        </label>
                        <p className="text-sm mt-1">{selectedSegment.overlay.text}</p>
                      </div>
                    </>
                  )}

                  {selectedSegment.similarity_score !== null && selectedSegment.similarity_score !== undefined && (
                    <>
                      <Separator />
                      <div>
                        <label className="text-xs text-muted-foreground uppercase tracking-wide">
                          Match Score
                        </label>
                        <p className="text-sm mt-1">
                          {(selectedSegment.similarity_score * 100).toFixed(0)}% match
                        </p>
                      </div>
                    </>
                  )}

                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleOpenClipSwap(selectedSegment)}
                    >
                      <RefreshCw className="mr-2 h-4 w-4" />
                      Swap Clip
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => {
                        setSwapSegment(selectedSegment);
                        setClipSwapOpen(true);
                      }}
                    >
                      <Settings className="mr-2 h-4 w-4" />
                      Edit
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Click a segment in the timeline to view details
                </p>
              )}
            </CardContent>
          </Card>

          {/* Render history */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Film className="h-4 w-4" />
                Render History
              </CardTitle>
            </CardHeader>
            <CardContent>
              {rendersLoading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : rendersData?.renders && rendersData.renders.length > 0 ? (
                <ScrollArea className="h-[200px]">
                  <div className="space-y-2">
                    {rendersData.renders.map((render) => (
                      <div
                        key={render.id}
                        className={`p-2 rounded-lg border cursor-pointer transition-colors ${
                          activeRenderId === render.id
                            ? 'border-primary bg-primary/5'
                            : 'hover:bg-muted/50'
                        }`}
                        onClick={() => setActiveRenderId(render.id)}
                      >
                        <div className="flex items-center justify-between">
                          <span className={renderStatusConfig[render.status].color}>
                            {renderStatusConfig[render.status].icon}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {formatDistanceToNow(new Date(render.created_at), {
                              addSuffix: true,
                            })}
                          </span>
                        </div>
                        <p className="text-xs mt-1 text-muted-foreground">
                          {render.composition_id.replace('_v1', '').replace('_', ' ')}
                        </p>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No renders yet
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Timeline Editor */}
      {currentPayload && (
        <TimelineEditor
          payload={currentPayload}
          selectedSegmentId={selectedSegment?.id || null}
          currentFrame={currentFrame}
          onSegmentClick={handleSegmentClick}
          onSegmentUpdate={handleSegmentUpdate}
          onSeek={handleSeek}
          onOpenClipSwap={handleOpenClipSwap}
        />
      )}

      {/* Clip Swap Modal */}
      <ClipSwapModal
        open={clipSwapOpen}
        onOpenChange={setClipSwapOpen}
        segment={swapSegment}
        projectId={id}
        onSwapClip={handleSwapClip}
        onRegenerateBRoll={handleRegenerateBRoll}
        onUpdateOverlay={handleUpdateOverlay}
        onUpdateDuration={handleUpdateDuration}
        alternativeClips={alternativeClips}
        isLoadingAlternatives={isLoadingAlternatives}
        onSearchClips={handleSearchClips}
      />
    </div>
  );
}
