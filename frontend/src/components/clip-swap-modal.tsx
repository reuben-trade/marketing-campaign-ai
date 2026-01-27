'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Slider } from '@/components/ui/slider';
import {
  Loader2,
  Search,
  Video,
  Wand2,
  Clock,
  Check,
  RefreshCw,
  AlertCircle,
  FileVideo,
  Sparkles,
} from 'lucide-react';
import type { TimelineSegment, VideoClipSource } from '@/types/render';
import type { UserVideoSegment } from '@/types/project';

// Alternative clip interface (combining segment data with selection metadata)
interface AlternativeClip {
  id: string;
  segment: UserVideoSegment;
  similarity_score: number;
  selected?: boolean;
}

export interface ClipSwapModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  segment: TimelineSegment | null;
  projectId: string;
  onSwapClip: (segmentId: string, newSource: VideoClipSource) => void;
  onRegenerateBRoll?: (segmentId: string, prompt: string) => void;
  onUpdateOverlay?: (segmentId: string, text: string) => void;
  onUpdateDuration?: (segmentId: string, durationFrames: number) => void;
  alternativeClips?: AlternativeClip[];
  isLoadingAlternatives?: boolean;
  onSearchClips?: (query: string) => void;
}

/**
 * ClipSwapModal component for replacing clips in the timeline.
 * Features:
 * - View alternative clips from semantic search
 * - Search for new clips with custom query
 * - Preview clips before selecting
 * - Edit overlay text
 * - Adjust segment duration
 * - Regenerate B-Roll with modified prompt
 */
export function ClipSwapModal({
  open,
  onOpenChange,
  segment,
  onSwapClip,
  onRegenerateBRoll,
  onUpdateOverlay,
  onUpdateDuration,
  alternativeClips = [],
  isLoadingAlternatives = false,
  onSearchClips,
}: ClipSwapModalProps) {
  const [activeTab, setActiveTab] = useState<'alternatives' | 'search' | 'broll' | 'edit'>('alternatives');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);
  const [overlayText, setOverlayText] = useState('');
  const [brollPrompt, setBrollPrompt] = useState('');
  const [durationFrames, setDurationFrames] = useState(0);

  // Initialize state when segment changes
  useEffect(() => {
    if (segment) {
      setSearchQuery(segment.search_query || '');
      setOverlayText(segment.overlay?.text || '');
      setBrollPrompt(segment.generated_source?.generation_prompt || '');
      setDurationFrames(segment.duration_frames);
      setSelectedClipId(null);

      // Set initial tab based on segment type
      if (segment.type === 'generated_broll') {
        setActiveTab('broll');
      } else if (alternativeClips.length > 0) {
        setActiveTab('alternatives');
      } else {
        setActiveTab('search');
      }
    }
  }, [segment, alternativeClips.length]);

  // Handle search
  const handleSearch = useCallback(() => {
    if (searchQuery.trim() && onSearchClips) {
      onSearchClips(searchQuery.trim());
    }
  }, [searchQuery, onSearchClips]);

  // Handle clip selection
  const handleSelectClip = useCallback((clip: AlternativeClip) => {
    setSelectedClipId(clip.id);
  }, []);

  // Handle swap confirmation
  const handleConfirmSwap = useCallback(() => {
    if (!segment || !selectedClipId) return;

    const selectedClip = alternativeClips.find((c) => c.id === selectedClipId);
    if (!selectedClip) return;

    const newSource: VideoClipSource = {
      url: selectedClip.segment.source_file_url || '',
      start_time: selectedClip.segment.timestamp_start,
      end_time: selectedClip.segment.timestamp_end,
    };

    onSwapClip(segment.id, newSource);
    onOpenChange(false);
  }, [segment, selectedClipId, alternativeClips, onSwapClip, onOpenChange]);

  // Handle B-Roll regeneration
  const handleRegenerateBRoll = useCallback(() => {
    if (!segment || !brollPrompt.trim() || !onRegenerateBRoll) return;
    onRegenerateBRoll(segment.id, brollPrompt.trim());
  }, [segment, brollPrompt, onRegenerateBRoll]);

  // Handle overlay text update
  const handleUpdateOverlay = useCallback(() => {
    if (!segment || !onUpdateOverlay) return;
    onUpdateOverlay(segment.id, overlayText);
    onOpenChange(false);
  }, [segment, overlayText, onUpdateOverlay, onOpenChange]);

  // Handle duration update
  const handleUpdateDuration = useCallback(() => {
    if (!segment || !onUpdateDuration) return;
    onUpdateDuration(segment.id, durationFrames);
  }, [segment, durationFrames, onUpdateDuration]);

  // Calculate duration display
  const fps = 30; // Default FPS
  const durationSeconds = durationFrames / fps;
  const minDuration = 15; // 0.5 seconds at 30fps
  const maxDuration = 300; // 10 seconds at 30fps

  if (!segment) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {segment.type === 'video_clip' ? (
              <Video className="h-5 w-5" />
            ) : segment.type === 'generated_broll' ? (
              <Wand2 className="h-5 w-5" />
            ) : (
              <FileVideo className="h-5 w-5" />
            )}
            {segment.beat_type ? `Edit ${segment.beat_type} Segment` : 'Edit Segment'}
          </DialogTitle>
          <DialogDescription>
            {segment.type === 'video_clip'
              ? 'Choose a different clip or edit this segment'
              : segment.type === 'generated_broll'
              ? 'Modify the B-Roll generation prompt or replace with a clip'
              : 'Edit this segment'}
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="alternatives" disabled={segment.type === 'generated_broll' && !alternativeClips.length}>
              Alternatives
            </TabsTrigger>
            <TabsTrigger value="search">Search</TabsTrigger>
            {segment.type === 'generated_broll' && (
              <TabsTrigger value="broll">B-Roll</TabsTrigger>
            )}
            <TabsTrigger value="edit">Edit</TabsTrigger>
          </TabsList>

          {/* Alternatives Tab */}
          <TabsContent value="alternatives" className="mt-4">
            {isLoadingAlternatives ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Loading alternatives...</span>
              </div>
            ) : alternativeClips.length > 0 ? (
              <ScrollArea className="h-[300px]">
                <div className="grid grid-cols-2 gap-3 pr-4">
                  {alternativeClips.map((clip) => (
                    <div
                      key={clip.id}
                      className={`relative rounded-lg border-2 cursor-pointer transition-all overflow-hidden ${
                        selectedClipId === clip.id
                          ? 'border-primary bg-primary/5'
                          : 'border-transparent bg-muted/50 hover:border-muted-foreground/30'
                      }`}
                      onClick={() => handleSelectClip(clip)}
                    >
                      {/* Thumbnail */}
                      <div className="relative aspect-video bg-black">
                        {clip.segment.thumbnail_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={clip.segment.thumbnail_url}
                            alt={clip.segment.visual_description || 'Clip preview'}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Video className="h-8 w-8 text-muted-foreground" />
                          </div>
                        )}

                        {/* Selection indicator */}
                        {selectedClipId === clip.id && (
                          <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
                            <Check className="h-8 w-8 text-primary" />
                          </div>
                        )}

                        {/* Similarity badge */}
                        <Badge
                          className="absolute top-2 right-2"
                          variant={clip.similarity_score >= 0.8 ? 'default' : 'secondary'}
                        >
                          {Math.round(clip.similarity_score * 100)}% match
                        </Badge>

                        {/* Duration */}
                        <Badge variant="secondary" className="absolute bottom-2 left-2">
                          <Clock className="h-3 w-3 mr-1" />
                          {clip.segment.duration_seconds?.toFixed(1)}s
                        </Badge>
                      </div>

                      {/* Description */}
                      <div className="p-2">
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {clip.segment.visual_description || 'No description'}
                        </p>
                        {clip.segment.action_tags && clip.segment.action_tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {clip.segment.action_tags.slice(0, 3).map((tag) => (
                              <Badge key={tag} variant="outline" className="text-[10px]">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <AlertCircle className="h-8 w-8 mb-2 opacity-50" />
                <p className="text-sm">No alternative clips available</p>
                <p className="text-xs mt-1">Try searching for clips with a different query</p>
              </div>
            )}
          </TabsContent>

          {/* Search Tab */}
          <TabsContent value="search" className="mt-4">
            <div className="space-y-4">
              <div className="flex gap-2">
                <div className="flex-1">
                  <Label htmlFor="search-query" className="sr-only">
                    Search query
                  </Label>
                  <Input
                    id="search-query"
                    placeholder="Describe the clip you're looking for..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSearch();
                    }}
                  />
                </div>
                <Button onClick={handleSearch} disabled={!searchQuery.trim()}>
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
              </div>

              {segment.search_query && (
                <div className="text-xs text-muted-foreground">
                  <span className="font-medium">Original query:</span> {segment.search_query}
                </div>
              )}

              <Separator />

              <div className="text-center py-8 text-muted-foreground">
                <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Enter a search query to find clips</p>
                <p className="text-xs mt-1">
                  Describe visual elements, actions, or emotions you want
                </p>
              </div>
            </div>
          </TabsContent>

          {/* B-Roll Tab */}
          {segment.type === 'generated_broll' && (
            <TabsContent value="broll" className="mt-4">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="broll-prompt">Generation Prompt</Label>
                  <Textarea
                    id="broll-prompt"
                    placeholder="Describe the B-Roll you want to generate..."
                    value={brollPrompt}
                    onChange={(e) => setBrollPrompt(e.target.value)}
                    rows={3}
                    className="mt-2"
                  />
                </div>

                {segment.generated_source?.generation_prompt && (
                  <div className="text-xs text-muted-foreground">
                    <span className="font-medium">Original prompt:</span>{' '}
                    {segment.generated_source.generation_prompt}
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <Badge variant="secondary">
                    <Sparkles className="h-3 w-3 mr-1" />
                    AI-Generated
                  </Badge>
                  {segment.generated_source?.regenerate_available && (
                    <Badge variant="outline">Regeneration available</Badge>
                  )}
                </div>

                <Button
                  onClick={handleRegenerateBRoll}
                  disabled={!brollPrompt.trim() || !onRegenerateBRoll}
                  className="w-full"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Regenerate B-Roll
                </Button>

                <p className="text-xs text-muted-foreground text-center">
                  B-Roll generation uses Veo 2. This may take a moment.
                </p>
              </div>
            </TabsContent>
          )}

          {/* Edit Tab */}
          <TabsContent value="edit" className="mt-4">
            <div className="space-y-6">
              {/* Overlay text editing */}
              {(segment.overlay || segment.type === 'video_clip') && (
                <div>
                  <Label htmlFor="overlay-text">Overlay Text</Label>
                  <Input
                    id="overlay-text"
                    placeholder="Text to display on this segment..."
                    value={overlayText}
                    onChange={(e) => setOverlayText(e.target.value)}
                    className="mt-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    This text will appear over the video clip
                  </p>
                </div>
              )}

              {/* Duration adjustment */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label>Duration</Label>
                  <span className="text-sm font-medium">{durationSeconds.toFixed(1)}s</span>
                </div>
                <Slider
                  value={[durationFrames]}
                  min={minDuration}
                  max={maxDuration}
                  step={1}
                  onValueChange={(value) => setDurationFrames(value[0])}
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-1">
                  <span>{(minDuration / fps).toFixed(1)}s</span>
                  <span>{(maxDuration / fps).toFixed(1)}s</span>
                </div>
              </div>

              {/* Segment info */}
              <div className="bg-muted/50 rounded-lg p-3">
                <h4 className="text-sm font-medium mb-2">Segment Info</h4>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <dt className="text-muted-foreground">Type</dt>
                  <dd className="capitalize">{segment.type.replace('_', ' ')}</dd>
                  <dt className="text-muted-foreground">Beat Type</dt>
                  <dd className="capitalize">{segment.beat_type || 'None'}</dd>
                  <dt className="text-muted-foreground">Start Frame</dt>
                  <dd>{segment.start_frame}</dd>
                  <dt className="text-muted-foreground">Frames</dt>
                  <dd>{segment.duration_frames}</dd>
                </dl>
              </div>

              <Button
                onClick={() => {
                  handleUpdateOverlay();
                  handleUpdateDuration();
                }}
                disabled={!onUpdateOverlay && !onUpdateDuration}
                className="w-full"
              >
                <Check className="h-4 w-4 mr-2" />
                Save Changes
              </Button>
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {(activeTab === 'alternatives' || activeTab === 'search') && (
            <Button onClick={handleConfirmSwap} disabled={!selectedClipId}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Swap Clip
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ClipSwapModal;
